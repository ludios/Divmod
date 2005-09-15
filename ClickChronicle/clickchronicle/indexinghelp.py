from zope.interface import Interface, implements
from axiom.item import Item
from axiom import attributes
from xapwrap.index import SmartIndex, ParsedQuery
from xapwrap.document import Document, TextField, Keyword, StandardAnalyzer, Term

XAPIAN_INDEX_DIR = 'xap.index'

class IIndexer(Interface):
    """
    Interface for providing full-text indexing services.
    """

    def index(self, item):
        """
        Index and item for later search.
        """

    def search(self, aString):
        """
        Search the index for aString and return results.
        """

    def count(self, aString):
        """
        Return a 2-tuple of (estimated-matches, total-docs-indexed)
        """
        

class IIndexable(Interface):
    """
    Something that can be indexed by an IIndexer.
    """

    def asDocument(self):
        """Return a Deferred that reutrns a xapwrap.Document
        containing the text and fields for indexing by IIndexer.
        """

    
class SyncIndexer(Item):
    """
    Implements a synchronous in-process full-text indexer.
    """
    
    schemaVersion = 1
    typeName = 'syncindexer'
    indexCount = attributes.integer(default=0)
    
    implements(IIndexer)

    def installOn(self, other):
        other.powerUp(self, IIndexer)

    def index(self, item):
        def cbIndex(doc):
            xapDir = self.store.newDirectory(XAPIAN_INDEX_DIR)
            xapIndex = SmartIndex(str(xapDir.path), True)
            xapIndex.index(doc)
            xapIndex.close()
            return doc
        d = IIndexable(item).asDocument()
        d.addCallback(cbIndex)
        return d

    def delete(self, item):
        xapDir = self.store.newDirectory(XAPIAN_INDEX_DIR)
        xapIndex = SmartIndex(str(xapDir.path), True)
        xapIndex.delete_document(item.storeID)
        xapIndex.close()

    def search(self, aString, **kwargs):
        xapDir = self.store.newDirectory(XAPIAN_INDEX_DIR)
        xapIndex = SmartIndex(str(xapDir.path), True)
        result = xapIndex.search(aString, **kwargs)
        xapIndex.close()
        return result

    def count(self, aString):
        xapDir = self.store.newDirectory(XAPIAN_INDEX_DIR)
        xapIndex = SmartIndex(str(xapDir.path), True)
        query = ParsedQuery(aString).prepare(xapIndex.qp)
        count = xapIndex.count(query)
        xapIndex.close()
        return count
        
# extract meta tags from a HTML document
# (based on sgmllib-example-1 in the effbot guide)
# START COPY - Copied from http://mail.python.org/pipermail/python-list/2001-January/023700.html
import sgmllib

class ExtractMeta(sgmllib.SGMLParser):

    def __init__(self, verbose=0):
        sgmllib.SGMLParser.__init__(self, verbose)
        self.meta = []
        
    def do_meta(self, attrs):
        name = content = None
        for k, v in attrs:
            if k == "name":
                name = v
            if k == "content":
                content = v
        if name and content:
            self.meta.append((name, content))
                            
    def end_title(self):
        # ignore meta tags after </title>.  you
        # can comment away this method if you
        # want to parse the entire file
        raise EOFError
    
def getMeta(source):
    """
    Extract meta tags from an HTML doc.
    """
    p = ExtractMeta()
    try:
        p.feed(source)
    except EOFError:
        pass
    return p.meta

# END COPYING

from twisted.web import client
def getPageSource(url):
    """Asynchronously get the page source for a URL.
    """
        
    return client.getPage(url)    

import re
rawstr = r"""<.*?>"""
tag_re = re.compile(rawstr,  re.IGNORECASE| re.DOTALL)
rawstr = r"""<n?o?script.*?</n?o?script>"""
script_re = re.compile(rawstr,  re.IGNORECASE| re.MULTILINE| re.DOTALL)
rawstr = r"""&nbsp"""
nbsp_re = re.compile(rawstr,  re.IGNORECASE| re.MULTILINE| re.DOTALL)

def getText(source):
    """
    Get all the text from an HTML doc.
    """
    #doc = microdom.parseString(source, beExtremelyLenient=True)
    #text = domhelpers.gatherTextNodes(doc)
    noScript = script_re.subn(' ', source)[0]
    noTags = tag_re.subn(' ', noScript)[0]
    text = nbsp_re.subn(' ', noTags)[0]
    return text

def makeDocument(visit, pageSource):
    keywords = [
        Keyword('type', 'url'),
        Keyword('url', visit.url),
        Keyword('title', visit.title)]
    text = getText(pageSource)
    # Get meta tag text and add it as non-positional terms
    metaDict = getMeta(pageSource)
    terms = []
    if metaDict:
        sa = StandardAnalyzer()
        for k, v in metaDict:
            toks = sa.tokenize(v)
            for tok in toks:
                terms.append(Term(tok))
    # Add page text
    textFields = [TextField(text)]
    # Use storeID for possibly simpler removal of visit from index at a later stage
    doc = Document(uid=visit.storeID,
                   textFields=textFields,
                   keywords=keywords,
                   terms=terms,
                   source=pageSource)
    return doc
    
if __name__ == '__main__':
    import sys
    fnames = sys.argv[1:]
    for fname in fnames:
        print fname
        source = open(fname, 'rb').read()
        print getMeta(source)
        print '***********'
        print getText(source)
        
        

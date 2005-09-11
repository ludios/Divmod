from zope.interface import Interface, implements
from axiom.item import Item
from axiom import attributes
from xapwrap.xapwrap import SmartIndex


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

from twisted.web import microdom, domhelpers, client
def getPageSource(url):
    """Asynchronously get the page source for a URL.
    """
        
    return client.getPage(url)    

import re
rawstr = r"""<.*?>"""
compiled_re = re.compile(rawstr,  re.IGNORECASE| re.DOTALL)

def getText(source):
    """
    Get all the text from an HTML doc.
    """
    #doc = microdom.parseString(source, beExtremelyLenient=True)
    #text = domhelpers.gatherTextNodes(doc)
    text = compiled_re.subn(' ', source)[0]
    return text


from xapwrap.xapwrap import Document, TextField, SortKey, Keyword, StandardAnalyzer

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
                terms.append(tok)
    # Add page text
    textFields = [TextField(text)]
    # Use storeID for possibly simpler removal of visit from index at a later stage
    doc = Document(uid=visit.storeID,
                   textFields=textFields,
                   keywords=keywords,
                   terms=terms,
                   source=pageSource)
    return doc
    

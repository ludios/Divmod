from zope.interface import implements
from axiom.item import Item
from axiom import attributes
from xapwrap.index import SmartIndex, ParsedQuery, DocNotFoundError
from xapwrap.document import Document, TextField, StandardAnalyzer, Term, Value
from clickchronicle import tagstrip
from clickchronicle.iclickchronicle import IIndexer, IIndexable

XAPIAN_INDEX_DIR = 'xap.index'

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

    def _setIndexCount(self, newCount):
        def txn():
            self.indexCount = newCount
        self.store.transact(txn)
        
    def incrementIndexCount(self):
        self._setIndexCount(self.indexCount + 1)

    def decrementIndexCount(self):
        self._setIndexCount(self.indexCount - 1)
        
    def index(self, item):
        def cbIndex(doc):
            self.incrementIndexCount()
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
        try:
            xapIndex.delete_document(item.storeID)
        except DocNotFoundError:
            pass
        else:
            self.decrementIndexCount()
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
        
from twisted.web import client
def getPageSource(url):
    """Asynchronously get the page source for a URL.
    """
        
    return client.getPage(url)    

def makeDocument(visit, pageSource):
    values = [
        Value('type', 'url'),
        Value('url', visit.url),
        Value('title', visit.title)]
    (text, meta) = tagstrip.cook(pageSource)
    terms = []
    if meta:
        sa = StandardAnalyzer()
        for contents in meta.itervalues():
            for value in contents:
                for tok in sa.tokenize(value):
                    terms.append(Term(tok))
    # Add page text
    textFields = [TextField(text)]
    # Use storeID for possibly simpler removal of visit from index at a later stage
    doc = Document(uid=visit.storeID,
                   textFields=textFields,
                   values=values,
                   terms=terms,
                   source=pageSource)
    return doc
    
if __name__ == '__main__':
    import sys
    fnames = sys.argv[1:]
    for fname in fnames:
        print fname
        source = open(fname, 'rb').read()
        (text, meta) = tagstrip.cook(source)
        print meta
        print '***********'
        print text
        
        

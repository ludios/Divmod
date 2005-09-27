from zope.interface import implements
from axiom.item import Item
from axiom import attributes
from nevow.url import URL
from xapwrap.index import SmartIndex, ParsedQuery, DocNotFoundError
from xapwrap.document import Document, TextField, StandardAnalyzer, Term, Value
from clickchronicle import tagstrip, webclient
from clickchronicle.iclickchronicle import IIndexer, IIndexable, ICache
from clickchronicle.util import maybeDeferredWrapper

from twisted.internet import reactor, defer

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
        xapIndex = SmartIndex(str(xapDir.path), False)
        result = xapIndex.search(aString, **kwargs)
        xapIndex.close()
        return result

    def count(self, aString):
        xapDir = self.store.newDirectory(XAPIAN_INDEX_DIR)
        xapIndex = SmartIndex(str(xapDir.path), False)
        query = ParsedQuery(aString).prepare(xapIndex.qp)
        count = xapIndex.count(query)
        xapIndex.close()
        return count

from twisted.web import static
from xmantissa import ixmantissa, website

class FavIcon(Item, website.PrefixURLMixin):
    implements(ixmantissa.ISiteRootPlugin)

    data = attributes.bytes(allowNone=False)
    prefixURL = attributes.bytes(allowNone=False)
    contentType = attributes.bytes(allowNone=False)

    schemaVersion = 1
    typeName = 'favicon'

    def createResource(self):
        return static.Data(self.data, self.contentType)


from twisted.web import client
class CacheManager(Item):
    """
    Implements interfaces to fetch and cache data from external
    sources.
    """

    schemaVersion = 1
    typeName = 'cachemananger'
    cacheCount = attributes.integer(default=0)
    cacheSize = attributes.integer(default=0)

    implements(ICache)

    def installOn(self, other):
        other.powerUp(self, ICache)

    def rememberVisit(self, visit, domain, cacheIt=False, indexIt=True, storeFavicon=True):
        """
        XXX This is a bit of a mess right now. This is partially due to
        XXX the demands of testing and needs to be re-thought.

        This is how it should work:
        1. Fetch the page source.
        2. Somehow get the encoding, from the connection or the document
        3. Decode the whole page using the encoding
        4. Extract the title as unicode and set it on the visit (assuming we don't have it)
        5. Extract the meta tags as unicode
        6. Extract the text as unicode
        7. Index the unicode for text, title and tags
        7. Optionally cache the page source, encoded as it came off the wire.
        9. Fetch the favicon if needed.

        This method should be split into a few other methods all of
        which return deferreds and take a visit as an argument.
        """

        def cbCachePage(doc):
            """
            Cache the source for this visit.
            """
            newFile = self.store.newFile(self.cachedFileNameFor(visit).path)
            try:
                src = doc.source
            except AttributeError:
                # XXX - This is for the tests
                # fix this with some smarter tests
                src = ''
            newFile.write(src)
            newFile.close()
            return visit.domain
        d = None
        if indexIt:
            indexer = IIndexer(self.store)
            d=indexer.index(visit)
        else:
            d=defer.succeed(None)
        if cacheIt:
            if d is None:
                d = visit.asDocument()
            d.addCallback(cbCachePage)
        if domain.favIcon is None and storeFavicon:
            faviconSuccess = self.fetchFavicon(domain)
        else:
            faviconSuccess = defer.succeed(None)

        futureVisit = defer.gatherResults((faviconSuccess, d))
        return futureVisit.addBoth(lambda ign: visit)

    #rememberVisit = maybeDeferredWrapper(rememberVisit)

    def cachedFileNameFor(self, visit):
        """
        Return the path to the cached source for this visit.
        The path consists of the iso date for the visit as directory and the
        storeID as the filename.
        e.g. cchronicle.axiom/files/account/test.com/user/files/cache/2005-09-10/55.html
        """
        dirName = visit.timestamp.asDatetime().date().isoformat()
        cacheDir = self.store.newDirectory('cache/%s' % dirName)
        fileName = cacheDir.child('%s.html' % visit.storeID)
        return fileName

    def forget(self, visit):
        try:
            self.cachedFileNameFor(visit).remove()
        except OSError:
            pass

    def fetchFavicon(self, domain):
        def gotFavicon((data, (contentType,))):
            if contentType:
                contentType = contentType[0]
            else:
                contentType = 'image/x-icon'

            s = self.store
            def txn():
                fi = FavIcon(prefixURL='private/icons/%s.ico' % domain.url,
                             data=data, contentType=contentType, store=s)
                fi.installOn(s)
                domain.favIcon = fi
            s.transact(txn)

        url = str(URL(netloc=domain.url, pathsegs=('favicon.ico',)))
        d = webclient.getPageAndHeaders(['content-type'], url)
        d.addCallback(gotFavicon)
        return d


    def getPageSource(self, url):
        """Asynchronously get the page source for a URL.
        """
        def gotPage(result):
            source, headers = result
            print 'Discovered headers for', repr(url), 'tobe', repr(headers)
            contentType = headers[0]
            if contentType:
                encoding = _parseContentType(contentType[0])
                print 'Discovered', repr(encoding), 'as encoding for', repr(url)
                return source, encoding
            return source, None

        return webclient.getPageAndHeaders(
            ['content-type'], url).addCallback(gotPage)

def _parseContentType(ctype):
    # ctype should be something like this 'text/html; charset=iso-8859-1'
    parts = ctype.lower().split(';', 1)
    if len(parts) == 1:
        return None
    type, args = parts
    for arg in args.split(';'):
        parts = arg.split('=')
        if len(parts) == 2 and parts[0].strip() == 'charset':
            return parts[1].strip()
    return None

def _getEncoding(meta):
    # TODO This should really be coming from the http encoding
    if 'http-equiv' in meta:
        equivs=meta['http-equiv']
        if 'content-type' in equivs:
            ctype = equivs['content-type']
            return _parseContentType(ctype)
    return None

CHARSET_SEARCH_LIMIT = 2048 # The charset must appear within this number of characters
def makeDocument(visit, pageSource, encoding=None):
    title = visit.title # TODO - Should get the title from BeautifulSoup

    if encoding is None:
        (ignore, meta)=tagstrip.cook(pageSource[:CHARSET_SEARCH_LIMIT])
        encoding = _getEncoding(meta)
    if encoding is None:
        encoding = 'ascii'

    title = title.decode(encoding, 'replace')
    decodedSource = pageSource.decode(encoding, 'replace')

    (text, meta) = tagstrip.cook(decodedSource)
        
    values = [
        Value('type', 'url'),
        Value('url', visit.url),
        Value('title', title)]
    terms = []
    #if meta:
    #    sa = StandardAnalyzer()
    #    for contents in meta.itervalues():
    #        for value in contents:
    #            for tok in sa.tokenize(value):
    #                terms.append(Term(tok))

    # Add page text
    textFields = [TextField(text)]
    if visit.title:
        textFields.append(TextField(visit.title))
    # Use storeID for simpler removal of visit from index at a later stage
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
        source =source.decode('utf-8')
        (text, meta) = tagstrip.cook(source)

        print meta
        print '***********'
        print type(text)
        #print text.decode('utf-8')

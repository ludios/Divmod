from zope.interface import implements
from twisted.python import failure
from twisted.web import error as weberror
from axiom.item import Item
from axiom import attributes
from nevow.url import URL
from xapwrap.index import SmartIndex, ParsedQuery, DocNotFoundError
from xapwrap.document import Document, TextField, Value, Keyword
from clickchronicle import tagstrip, webclient
from clickchronicle.iclickchronicle import IIndexer, ICache
from clickchronicle.pageinfo import getPageInfo
from clickchronicle.imagedetect import getImageType
from clickchronicle import queue


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

    def decrementIndexCount(self, decrement=1):
        self._setIndexCount(self.indexCount - decrement)

    def index(self, doc):
        self.incrementIndexCount()
        xapDir = self.store.newDirectory(XAPIAN_INDEX_DIR)
        xapIndex = SmartIndex(str(xapDir.path), True)
        xapIndex.index(doc)
        xapIndex.close()

    def delete(self, item):
        xapDir = self.store.newDirectory(XAPIAN_INDEX_DIR)
        xapIndex = SmartIndex(str(xapDir.path), True)
        try:
            xapIndex.delete_document('_STOREID'+str(item.storeID))
        except DocNotFoundError:
            pass
        else:
            self.decrementIndexCount()
        xapIndex.close()

    def bulkDelete(self, itemList):
        xapDir = self.store.newDirectory(XAPIAN_INDEX_DIR)
        xapIndex = SmartIndex(str(xapDir.path), True)
        for item in itemList:
            try:
                xapIndex.delete_document('_STOREID'+str(item.storeID))
            except DocNotFoundError:
                pass
        self.decrementIndexCount(len(itemList))
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

from nevow import static
from xmantissa import ixmantissa, website

ICON_VALIDITY_TIME = 60 * 60 * 24

class FavIcon(Item, website.PrefixURLMixin):
    implements(ixmantissa.ISiteRootPlugin)

    data = attributes.bytes(allowNone=False)
    prefixURL = attributes.bytes(allowNone=False)
    iconURL = attributes.bytes(allowNone=False)
    contentType = attributes.bytes(allowNone=False)

    schemaVersion = 2
    typeName = 'favicon'

    def createResource(self):
        return static.Data(self.data, self.contentType, ICON_VALIDITY_TIME)

class DefaultFavicon(Item):

    iconURL = attributes.bytes(default='/static/images/favicon.png')

    schemaVersion = 1
    typeName = 'clickchronicle_default_favicon'

class PageFetchingTaskMixin(object):
    def retryableFailure(self, f):
        return f.check(weberror.Error) is not None

    def _ebGotSource(self, err):
        # return likely errors as TaskError so they aren't reported
        err.trap(weberror.Error)
        return failure.Failure(queue.TaskError("HTTP error while downloading page (%r)" % (err.getErrorMessage(),)))


class FetchFavIconTask(Item, PageFetchingTaskMixin):
    schemaVersion = 1
    typeName = 'clickchronicle_fetch_favicon_task'

    domain = attributes.reference()
    faviconURL = attributes.bytes()
    cacheMan = attributes.reference()

    def __repr__(self):
        return '<Fetching FavIcon for %r>' % (self.domain,)

    def do(self):
        futureFavicon = self.cacheMan.fetchFavicon(self.domain, faviconURL=self.faviconURL)
        futureFavicon.addErrback(self._ebGotSource)
        return futureFavicon

class FetchDomainTitleTask(Item, PageFetchingTaskMixin):
    schemaVersion = 1
    typeName = "clickchronicle_fetch_domain_title_task"

    domain = attributes.reference()
    cacheMan = attributes.reference()

    def __repr__(self):
        return "<Fetching %r>" % self.domain.url

    def do(self):
        futureSource = self.cacheMan.getPageSource(self.domain.url)
        futureSource.addCallbacks(self._cbGotSource, self._ebGotSource)
        return futureSource

    def _cbGotSource(self, (source, pageInfo)):
        if pageInfo.title is None:
            title = unicode(self.domain.url)
        else:
            title = pageInfo.title.decode(pageInfo.charset, "replace")

        self.domain.title = title

class FetchSourceTask(Item, PageFetchingTaskMixin):
    schemaVersion = 1
    typeName = 'clickchronicle_fetch_source_task'

    visit = attributes.reference()
    indexer = attributes.reference()
    cacheMan = attributes.reference()

    indexIt = attributes.boolean()
    cacheIt = attributes.boolean()
    storeFavicon = attributes.boolean()

    def __repr__(self):
        return '<Fetching %r>' % (self.visit.url,)

    def do(self):
        d = self.cacheMan.getPageSource(self.visit.url)
        d.addCallbacks(self._cbGotSource, self._ebGotSource)
        return d

    def _cbGotSource(self, (source, pageInfo)):
        if self.storeFavicon:
            self._enqueueFaviconTask(pageInfo)
        if self.indexIt:
            self._index(source, pageInfo)
        if self.cacheIt:
            self._cache(source, pageInfo)

    def _index(self, source, pageInfo):
        self.indexer.index(makeDocument(self.visit, source, pageInfo))

    def _cache(self, source, pageInfo):
        """
        Cache the source for this visit.
        """
        newFile = self.store.newFile(self.cacheMan.cachedFileNameFor(self.visit).path)
        newFile.write(source)
        newFile.close()

    def _enqueueFaviconTask(self, pageInfo):
        domain = self.visit.domain

        if domain.favIcon is self.store.findFirst(DefaultFavicon):
            for tsk in self.store.query(
                FetchFavIconTask,
                attributes.AND(FetchFavIconTask.domain == domain,
                               FetchFavIconTask.cacheMan == self.cacheMan)):
                break
            else:
                if pageInfo.faviconURL is not None:
                    absURL = str(URL.fromString(self.visit.url).click(pageInfo.faviconURL))
                else:
                    absURL = None

                self.cacheMan.tasks.addTask(
                    FetchFavIconTask(store=self.store,
                                     domain=domain,
                                     faviconURL=absURL,
                                     cacheMan=self.cacheMan))

class CacheManager(Item):
    """
    Implements interfaces to fetch and cache data from external
    sources.
    """

    schemaVersion = 1
    typeName = 'cachemananger'
    cacheCount = attributes.integer(default=0)
    cacheSize = attributes.integer(default=0)

    tasks = attributes.reference()

    implements(ICache)

    def __init__(self, **kw):
        super(CacheManager, self).__init__(**kw)
        self.tasks = queue.Queue(store=self.store)

    def installOn(self, other):
        other.powerUp(self, ICache)

    def rememberVisit(self, visit, cacheIt=False, indexIt=True, storeFavicon=True):
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

        if indexIt or cacheIt:
            self.tasks.addTask(
                FetchSourceTask(store=self.store,
                                visit=visit,
                                indexer=IIndexer(self.store),
                                cacheMan=self,
                                indexIt=indexIt,
                                cacheIt=cacheIt,
                                storeFavicon=storeFavicon))

        if visit.domain.title is None:
            url = URL.fromString(visit.url)
            if url.isRoot(url.pathList()):
                visit.domain.title = visit.title
            else:
                visit.domain.title = unicode(visit.domain.url)
                self.tasks.addTask(
                    FetchDomainTitleTask(store=self.store,
                                         domain=visit.domain,
                                         cacheMan=self))

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

    def fetchFavicon(self, domain, faviconURL=None):
        def gotFavicon((data, (contentType,))):
            if len(contentType) == 0 or not contentType[0].startswith("image"):
                contentType = getImageType(data)
                if contentType is None:
                    return
            else:
                contentType = contentType[0]

            s = self.store
            iconURL = '/private/icons/%s.ico' % url.netloc
            fi = FavIcon(prefixURL=iconURL[1:], iconURL=iconURL,
                         data=data, contentType=contentType, store=s)
            fi.installOn(s)
            domain.favIcon = fi

        if faviconURL is not None:
            url = URL.fromString(faviconURL)
        else:
            url = URL.fromString(domain.url).child("favicon.ico")

        d = webclient.getPageAndHeaders(['content-type'], str(url))
        d.addCallback(gotFavicon)
        return d


    def getPageSource(self, url, fallbackCharset="ascii"):
        """Asynchronously get the page source for a URL.
           default to fallbackCharset if we can't find a
           charset declaration in page headers or <meta>
           tags
        """
        def gotPage(result, fallbackCharset=fallbackCharset):
            source, headers = result
            contentType = headers[0]

            if contentType:
                encoding = _parseContentType(contentType[0])
                if encoding is not None:
                    fallbackCharset = encoding

            pageInfo = getPageInfo(source, charset=fallbackCharset)
            return source, pageInfo

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

def makeDocument(visit, pageSource, pageInfo, summaryLength=400):
    encoding = pageInfo.charset
    title = visit.title

    decodedSource = pageSource.decode(encoding, 'replace')

    text = tagstrip.cook(decodedSource)

    for tag in pageInfo.metaTags:
        if tag.get('name') == 'description':
            summary = tag.get('content')
            if summary is not None:
                break
    else:
        summary = text

    if summaryLength < len(summary):
        summary = summary[:summaryLength] + '...'

    values = [
        Value('type', 'click'),
        Value('url', visit.url),
        Value('title', title),
        Value('summary', summary),
        Value('_STOREID', visit.storeID),
        ]

    keywords = [
        Keyword('_STOREID', str(visit.storeID)),
        Keyword('_TYPE', 'click'),
        ]

    # Add page text
    textFields = [TextField(text), TextField(title)]
    # Use storeID for simpler removal of visit from index at a later stage
    doc = Document(textFields=textFields,
                   values=values,
                   keywords=keywords,
                   source=pageSource)
    return doc

from clickchronicle import upgraders

if __name__ == '__main__':
    import sys
    fnames = sys.argv[1:]
    for fname in fnames:
        print fname
        source = open(fname, 'rb').read()
        source =source.decode('utf-8')
        text = tagstrip.cook(source)

        print type(text)
        #print text.decode('utf-8')

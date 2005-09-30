import datetime
from zope.interface import implements
from twisted.python import log, failure
from twisted.web import error as weberror
from epsilon import extime
from axiom.item import Item
from axiom import attributes, iaxiom
from nevow.url import URL
from xapwrap.index import SmartIndex, ParsedQuery, DocNotFoundError
from xapwrap.document import Document, TextField, Value
from clickchronicle import tagstrip, webclient
from clickchronicle.iclickchronicle import IIndexer, ICache
from clickchronicle.pageinfo import getPageInfo

from twisted.internet import defer

XAPIAN_INDEX_DIR = 'xap.index'

class TaskError(Exception):
    """
    An error occurred while processing a particular task.  The task
    should be retried.  The error will not be logged.
    """

class _Task(Item):
    schemaVersion = 1
    typeName = 'clickchronicle_queued_task'

    task = attributes.reference()
    added = attributes.timestamp()
    retries = attributes.integer(default=0)
    maxRetries = attributes.integer()
    lastAttempt = attributes.timestamp()
    queue = attributes.reference()

    def do(self):
        return self.task.do()


class IndexQueue(Item):
    schemaVersion = 1
    typeName = 'clickchronicle_indexing_queue'

    rate = attributes.integer(default=3)
    interval = attributes.integer(default=5000)
    maxRetries = attributes.integer(default=3)

    _waitingForQuiet = attributes.inmemory()

    def activate(self):
        self._waitingForQuiet = []

    def _keepMeInMemory(self, passthrough):
        return passthrough

    def notifyOnQuiecence(self):
        if not self.store.count(_Task, _Task.queue == self):
            return defer.succeed(None)
        d = defer.Deferred()
        self._waitingForQuiet.append(d)
        d.addCallback(self._keepMeInMemory)
        return d

    def addTask(self, task, maxRetries=None):
        if maxRetries is None:
            maxRetries = self.maxRetries
        if self.store.count(_Task, _Task.queue == self):
            self._reschedule()
        _Task(store=self.store,
              task=task,
              added=extime.Time(),
              lastAttempt=extime.Time(),
              maxRetries=maxRetries,
              queue=self)

    def _cbTask(self, ignored, task):
        task.deleteFromStore()

    def _ebTask(self, err, task):
        if not err.check(TaskError):
            log.msg("Error processing task: %r" % (task,))
            log.err(err)

        if task.retries > task.maxRetries or not task.task.retryableFailure(err):
            log.msg("Giving up on %r" % (task.task,))
            task.deleteFromStore()
        else:
            task.retries += 1
            task.lastAttempt = extime.Time()

    def _cbRun(self, ignored):
        if self.store.count(_Task, _Task.queue == self):
            self._reschedule()
        else:
            dl = self._waitingForQuiet
            self._waitingForQuiet = []
            for d in dl:
                d.callback(None)

    def _reschedule(self):
        sch = iaxiom.IScheduler(self.store)
        sch.schedule(
            self,
            extime.Time() + datetime.timedelta(milliseconds=self.interval))

    def run(self):
        dl = []
        for task in self.store.query(_Task,
                                     _Task.queue == self,
                                     sort=_Task.lastAttempt.ascending,
                                     limit=self.rate):
            dl.append(task.do().addCallbacks(self._cbTask, self._ebTask, callbackArgs=(task,), errbackArgs=(task,)))
        defer.DeferredList(dl).addCallback(self._cbRun)


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


class FetchFavIconTask(Item):
    schemaVersion = 1
    typeName = 'clickchronicle_fetch_favicon_task'

    domain = attributes.reference()
    faviconURL = attributes.bytes()
    cacheMan = attributes.reference()

    def __repr__(self):
        return '<Fetching FavIcon for %r>' % (self.domain,)

    def do(self):
        return self.cacheMan.fetchFavicon(self.domain, faviconURL=self.faviconURL)

    def retryableFailure(self, f):
        return f.check(weberror) is not None
        
class FetchSourceTask(Item):
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

    def retryableFailure(self, f):
        return f.check(weberror.Error) is not None

    def _cbGotSource(self, (source, pageInfo)):
        if self.indexIt:
            self._index(source, pageInfo)
        if self.cacheIt:
            self._cache(source, pageInfo)
        if self.storeFavicon:
            self._enqueueFaviconTask(pageInfo)
    
    def _ebGotSource(self, err):
        err.trap(weberror.Error)
        return failure.Failure(TaskError("HTTP error while downloading page (%r)" % (err.getErrorMessage(),)))

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
        
        if domain.favIcon is None:
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
                # is there a better way to go about this?
                for partask in self.store.query(_Task, _Task.task == self):
                    partask.queue.addTask(FetchFavIconTask(store=self.store,
                                                           domain=domain,
                                                           faviconURL=absURL,
                                                           cacheMan=self.cacheMan))
                    break

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
        self.tasks = IndexQueue(store=self.store)

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

        if faviconURL is not None:
            url = URL.fromString(faviconURL)
        else:
            url = URL(netloc=domain.url, pathsegs=("favicon.ico",))
            
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
            print 'Discovered headers for', repr(url), 'tobe', repr(headers)
            contentType = headers[0]
            
            if contentType:
                encoding = _parseContentType(contentType[0])
                if encoding is not None:
                    fallbackCharset = encoding
            
            pageInfo = getPageInfo(source, charset=fallbackCharset)
            print 'Discovered', repr(pageInfo.charset), 'as encoding for', repr(url)
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

def makeDocument(visit, pageSource, pageInfo):
    encoding = pageInfo.charset
    title = visit.title

    title = title.decode(encoding, 'replace')
    decodedSource = pageSource.decode(encoding, 'replace')

    text = tagstrip.cook(decodedSource)
    
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
    textFields = [TextField(text), TextField(title)]
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
        text = tagstrip.cook(source)

        print type(text)
        #print text.decode('utf-8')

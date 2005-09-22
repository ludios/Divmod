from datetime import datetime, timedelta
from zope.interface import Interface, implements

from twisted.python.components import registerAdapter
from nevow.url import URL
from nevow import rend, inevow, tags

from epsilon.extime import Time

from axiom.item import Item
from axiom import attributes

from xmantissa import ixmantissa, webnav, website, webapp
from xmantissa.webgestalt import AuthenticationApplication

from clickchronicle import indexinghelp
from clickchronicle.util import PagedTableMixin, maybeDeferredWrapper
from clickchronicle.visit import Visit, Domain, BookmarkVisit
from clickchronicle.searchparser import parseSearchString

class SearchBox(Item):
    implements(ixmantissa.INavigableElement)
    typeName = 'clickchronicle_searchbox'
    schemaVersion = 1

    searchPattern = attributes.inmemory()
    formAction = attributes.inmemory()

    installedOn = attributes.reference()

    searches = attributes.integer(default=0)

    def installOn(self, other):
        assert self.installedOn is None, "Cannot install SearchBox on more than one thing"
        other.powerUp(self, ixmantissa.INavigableElement)
        self.installedOn = other

    def topPanelContent(self):
        translator = ixmantissa.IWebTranslator(self.installedOn, None)
        if translator is not None:
            docFactory = translator.getDocFactory('search-box-fragment')
            self.searchPattern = inevow.IQ(docFactory).patternGenerator('search')
            self.formAction = translator.linkTo(self.storeID)
            return self.searchPattern.fillSlots('action', self.formAction)
        return None

    def getTabs(self):
        return []

class CCPrivatePagedTable(website.AxiomFragment, PagedTableMixin):
    """adds some CC-specific display logic"""
    maxTitleLength = 70

    def __init__(self, original, docFactory=None):
        self.store = original.store
        website.AxiomFragment.__init__(self, original, docFactory)
        self.translator = ixmantissa.IWebTranslator(original.installedOn)
        self.clickList = original.store.query(ClickList).next()
        pagingPatterns = inevow.IQ(self.translator.getDocFactory('paging-patterns'))

        pgen = pagingPatterns.patternGenerator

        self.tablePattern = pgen('clickTable')
        self.pageNumbersPattern = pgen('pagingWidget')
        self.itemsPerPagePattern = pgen('itemsPerPage')
        self.navBarPattern = pgen('navBar')

    def makeScriptTag(self, src):
        return tags.script(type='application/x-javascript',
                           src=src)
    def head(self):
        return self.makeScriptTag('/static/js/paged-table.js')

    def handle_ignore(self, ctx, url):
        store = self.original.store
        # find any Visit with this url
        visit = store.query(Visit, Visit.url == url).next()
        IClickRecorder(store).ignoreVisit(visit)
        # rewind to the first page, to reflect changes
        return self.updateTable(ctx, self.startPage,
                                self.defaultItemsPerPage)

    def trimTitle(self, visitDict):
        title = visitDict['title']
        if self.maxTitleLength < len(title):
            visitDict['title'] = '%s...' % title[:self.maxTitleLength - 3]
        return visitDict

class ClickChronicleBenefactor(Item):
    '''i am responsible for granting priveleges to avatars,
       which equates to installing stuff in their store'''

    implements(ixmantissa.IBenefactor)
    typeName = 'clickchronicle_benefactor'
    schemaVersion = 1

    endowed = attributes.integer(default = 0)

    def endow(self, ticket, avatar):
        self.endowed += 1
        avatar.findOrCreate(webapp.PrivateApplication,
                            preferredTheme=u'cc-skin').installOn(avatar)

        for item in (website.WebSite, ClickList, DomainList, Preferences,
                     ClickRecorder, indexinghelp.SyncIndexer,
                     SearchBox, AuthenticationApplication):
            avatar.findOrCreate(item).installOn(avatar)

class ClickList(Item):
    """similar to Preferences, i am an implementor of INavigableElement,
       and PrivateApplication will find me when when it looks in the user's
       store"""

    implements(ixmantissa.INavigableElement)
    typeName = 'clickchronicle_clicklist'
    schemaVersion = 1

    installedOn = attributes.reference()
    clicks = attributes.integer(default = 0)


    def installOn(self, other):
        assert self.installedOn is None, "Cannot install ClickList on more than one thing"
        other.powerUp(self, ixmantissa.INavigableElement)
        self.installedOn = other

    def getTabs(self):
        '''show a link to myself in the navbar'''
        return [webnav.Tab('My Clicks', self.storeID, 0.2)]

    def topPanelContent(self):
        return None

class DomainList(Item):
    """similar to Preferences, i am an implementor of INavigableElement,
       and PrivateApplication will find me when when it looks in the user's
       store"""

    implements(ixmantissa.INavigableElement)
    typeName = 'clickchronicle_domainlist'
    schemaVersion = 1

    installedOn = attributes.reference()
    clicks = attributes.integer(default = 0)

    def installOn(self, other):
        assert self.installedOn is None, "Cannot install DomainList on more than one thing"
        other.powerUp(self, ixmantissa.INavigableElement)
        self.installedOn = other

    def getTabs(self):
        '''show a link to myself in the navbar'''
        return [webnav.Tab('My Domains', self.storeID, 0.1)]

    def topPanelContent(self):
        return None

class ClickListFragment(CCPrivatePagedTable):
    '''i adapt ClickList to INavigableFragment'''
    implements(ixmantissa.INavigableFragment)

    fragmentName = 'click-list-fragment'
    title = ''
    live = True

    def generateRowDicts(self, ctx, pageNumber, itemsPerPage):
        store = self.original.store
        offset = (pageNumber - 1) * itemsPerPage

        for v in store.query(Visit, sort = Visit.timestamp.descending,
                             limit = itemsPerPage, offset = offset):

            yield self.trimTitle(v.asDict())

    def countTotalItems(self, ctx):
        return IClickRecorder(self.original.store).visitCount

registerAdapter(ClickListFragment,
                ClickList,
                ixmantissa.INavigableFragment)

class DomainListFragment(CCPrivatePagedTable):
    '''i adapt DomainList to INavigableFragment'''
    implements(ixmantissa.INavigableFragment)

    fragmentName = 'domain-list-fragment'
    title = ''
    live = True

    def generateRowDicts(self, ctx, pageNumber, itemsPerPage):
        store = self.original.store
        offset = (pageNumber - 1) * itemsPerPage

        for v in store.query(Domain, sort = Domain.visitCount.descending,
                             limit = itemsPerPage, offset = offset):

            yield v.asDict()

    def countTotalItems(self, ctx):
        return self.original.clicks

registerAdapter(DomainListFragment,
                DomainList,
                ixmantissa.INavigableFragment)

class Preferences(Item):
    """I represent storeable, per-user preference information.
       I implement INavigableElement, so PrivateApplication will
       look for me in the user's store"""
    implements(ixmantissa.INavigableElement)
    typeName = 'clickchronicle_preferences'
    schemaVersion = 1

    displayName = attributes.bytes(default='none set')
    homepage = attributes.bytes(default='http://www.clickchronicle.com')

    def installOn(self, other):
        other.powerUp(self, ixmantissa.INavigableElement)

    def getTabs(self):
        return [webnav.Tab('Preferences', self.storeID, 0.0)]

    def topPanelContent(self):
        return None

class PreferencesFragment(rend.Fragment):
    """I will get an adapter for Preferences instances, who
       implements INavigableFragment"""
    implements(ixmantissa.INavigableFragment)

    fragmentName = 'preferences-fragment'
    title = ''
    live = True

    def head(self):
        return None

    def data_preferences(self, ctx, data):
        """return a dict of self.original's (Preferences instance) columns"""
        return dict(displayName = self.original.displayName,
                    homepage = self.original.homepage)

registerAdapter(PreferencesFragment,
                Preferences,
                ixmantissa.INavigableFragment)

class IClickRecorder(Interface):
    """
    ClickRecorder interface.
    """

class ClickRecorder(Item, website.PrefixURLMixin):
    """
    I exist independently of the rest of the application and accept
    HTTP requests at private/record, which i farm off to URLGrabber.
    """
    schemaVersion = 1
    implements(ixmantissa.ISiteRootPlugin, IClickRecorder)
    typeName = 'clickchronicle_clickrecorder'
    # Total number of clicks we have ever received
    clickCount = attributes.integer(default = 0)
    # Total number of visits currently in store. An optimization for
    # forgetting/maxCount.
    visitCount = attributes.integer(default = 0)
    prefixURL = 'private/record'
    # Caching needs to be provisioned/bestowed
    caching = True
    # Number of MRU visits to keep
    maxCount = attributes.integer(default=500)
    bookmarkVisit = attributes.inmemory()

    def installOn(self, other):
        super(ClickRecorder, self).installOn(other)
        other.powerUp(self, IClickRecorder)

    def activate(self):
        self.bookmarkVisit = self.store.findOrCreate(BookmarkVisit)

    def createResource(self):
        return URLGrabber(self)

    def recordClick(self, qargs, index=True):
        """
        Extract POST arguments and create a Visit object before indexing and caching.
        """
        url = qargs.get('url')
        if url is None:
            # No url, no deal.
            return
        title = qargs.get('title')
        if not title or title.isspace():
            title = url

        def storeReferee(referrer):
            def forget():
                if self.visitCount > self.maxCount:
                    self.forgetOldestVisit()

            futureSuccess = self.findOrCreateVisit(url, title,
                                                   referrer, index=index)
            return futureSuccess.addCallback(lambda ign: forget())

        ref = qargs.get('ref')

        if ref:
            # we got some value for "ref".  pass the referrer url to
            # findOrCreateVisit, using same for title, because on the
            # off chance that we didn't record the click when the user
            # was viewing the referrer page, we don't have much else
            # meaningful to use
            deferred = self.findOrCreateVisit(ref, ref, index=index)
            deferred.addCallback(storeReferee)
        else:
            # Most likely selected a bookmark/shortcut
            deferred = storeReferee(self.bookmarkVisit)

        return deferred

    def findOrCreateVisit(self, url, title, referrer=None, index=True):
        """
        Try to find a visit to the same url TODAY.
        If found update the timestamp and return it.
        Otherwise create a new Visit.
        """
        host = URL.fromString(url).netloc
        domain = self.store.findOrCreate(Domain, host=host, title=host)
        if domain and domain.ignore:
            return
        existingVisit = self.findVisitForToday(url)
        timeNow = Time.fromDatetime(datetime.now())

        if existingVisit:
            # Already visited today
            # XXX What should we do about referrer for existing visit
            # XXX we'll conveniently ignore it for now
            def _():
                existingVisit.timestamp = timeNow
                existingVisit.visitCount += 1
                existingVisit.domain.visitCount += 1
                return existingVisit
            return self.store.transact(_)

        # New visit today
        def _():
            visit = Visit(store = self.store,
                            url = url,
                            timestamp = timeNow,
                            title = title,
                            domain = domain,
                            referrer = referrer)
            self.visitCount += 1
            domainList = self.store.query(DomainList).next()
            domainList.clicks += 1
            self.clickCount += 1
            visit.visitCount += 1
            visit.domain.visitCount +=1
            return visit

        visit = self.store.transact(_)
        if index:
            return self.rememberVisit(visit).addCallback(lambda ign: visit)
        return visit

    findOrCreateVisit = maybeDeferredWrapper(findOrCreateVisit)

    def findVisitForToday(self, url):
        dtNow = datetime.now()
        timeNow = Time.fromDatetime(dtNow)
        todayBegin = dtNow.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrowBegin = (dtNow+timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        existingVisit = None
        for existingVisit in self.store.query(
            Visit,
            attributes.AND(Visit.timestamp >= Time.fromDatetime(todayBegin),
                           Visit.timestamp < Time.fromDatetime(tomorrowBegin),
                           Visit.url == url)):
            break
        return existingVisit

    def rememberVisit(self, visit):
        def cbCachePage(doc):
            """
            Cache the source for this visit.
            """
            newFile = self.store.newFile(self.cachedFileNameFor(visit).path)
            newFile.write(doc.source)
            newFile.close()
        indexer = indexinghelp.IIndexer(self.store)
        d=indexer.index(visit)
        if self.caching:
            d.addCallback(cbCachePage)
        return d

    def forgetVisit(self, visit):
        indexer = indexinghelp.IIndexer(self.store)
        indexer.delete(visit)
        try:
            self.cachedFileNameFor(visit).remove()
        except OSError:
            pass
        def _():
            visit.deleteFromStore()
            self.visitCount -= 1
        self.store.transact(_)

    def forgetOldestVisit(self):
        """
        Remove oldest Visit from the store, cache and index.
        """
        # XXX - This needs to be more sophisticated since there is a known race
        # condition for a Visit being deleted from the index before the page has
        # been fetched and indexed/cahced
        visit = self.store.query(Visit, sort=Visit.timestamp.ascending).next()
        self.forgetVisit(visit)

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

    def ignoreVisit(self, visit):
        def txn():
            # ignore the Domain
            visit.domain.ignore = 1
            for (i, similarVisit) in enumerate(self.store.query(Visit, Visit.domain == visit.domain)):
                self.forgetVisit(similarVisit)

        self.store.transact(txn)


class SearchClicks(CCPrivatePagedTable):
    implements(ixmantissa.INavigableFragment)

    fragmentName = 'search-fragment'
    title = ''
    live = True

    discriminator = None
    matchingClicks = 0

    def __init__(self, orig, docFactory=None):
        self.indexer = orig.store.query(indexinghelp.SyncIndexer).next()
        self.searchbox = orig
        CCPrivatePagedTable.__init__(self, orig, docFactory)

    def head(self):
        yield self.makeScriptTag('/static/js/search.js')
        yield CCPrivatePagedTable.head(self)

    def setSearchState(self, ctx):
        # this isn't great - make me a LivePage that somehow also shows tabs
        qargs = dict(URL.fromContext(ctx).queryList())
        # ignore duplicates & spurious variables
        discrim = qargs.get('discriminator')
        if discrim is None:
            # do something meaningful
            pass
        self.incrementSearches()

        discrim = ' '.join(parseSearchString(discrim))
        (estimated, total) = self.indexer.count(discrim)
        self.matchingClicks = estimated
        self.discriminator = discrim

    def data_searchTerm(self, ctx, data):
        if self.discriminator is None:
            self.setSearchState(ctx)
        return self.discriminator

    def goingLive(self, ctx, client):
        client.call('setSearchTerm', self.discriminator)
        CCPrivatePagedTable.goingLive(self, ctx, client)

    def countTotalItems(self, ctx):
        if self.discriminator is None:
            self.setSearchState(ctx)
        return self.matchingClicks

    def generateRowDicts(self, ctx, pageNumber, itemsPerPage):
        if self.discriminator is None:
            self.setSearchState(ctx)
        offset = (pageNumber - 1) * itemsPerPage
        specs = self.indexer.search(self.discriminator,
                                    startingIndex = offset,
                                    batchSize = itemsPerPage)
        store = self.original.store
        for spec in specs:
            visit = store.getItemByID(spec['uid'])
            yield self.trimTitle(visit.asDict())

    def incrementSearches(self):
        def txn():
            self.searchbox.searches += 1
        self.original.store.transact(txn)

registerAdapter(SearchClicks,
                SearchBox,
                ixmantissa.INavigableFragment)

class URLGrabber(rend.Page):
    """I handle ClickRecorder's HTTP action.  i am not an Item
       because i have a lot of attributes inherited from rend.Page"""
    def __init__(self, recorder):
        self.recorder = recorder

    def renderHTTP(self, ctx):
        """get url and title GET variables, supplying sane defaults"""
        urlpath = inevow.IRequest(ctx).URLPath()
        qargs = dict(urlpath.queryList())
        self.recorder.recordClick(qargs)
        return ''

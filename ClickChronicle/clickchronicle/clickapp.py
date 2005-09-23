from datetime import datetime, timedelta
from zope.interface import implements

from twisted.python import util
from twisted.internet import reactor, defer
from twisted.python.components import registerAdapter
from twisted.web import client, static

from nevow.url import URL
from nevow import rend, inevow, tags, loaders

from epsilon.extime import Time

from axiom.item import Item
from axiom import userbase, attributes

from xmantissa import ixmantissa, webnav, website, webapp
from xmantissa.webgestalt import AuthenticationApplication

from clickchronicle import iclickchronicle
from clickchronicle import indexinghelp
from clickchronicle.util import PagedTableMixin, maybeDeferredWrapper
from clickchronicle.visit import Visit, Domain, BookmarkVisit
from clickchronicle.searchparser import parseSearchString

class FavIcon(Item, website.PrefixURLMixin):
    implements(ixmantissa.ISiteRootPlugin)
    
    data = attributes.bytes(allowNone=False)
    prefixURL = attributes.bytes(allowNone=False)
    contentType = attributes.bytes(allowNone=False)
    
    schemaVersion = 1
    typeName = 'favicon'

    def createResource(self):
        return static.Data(self.data, self.contentType)
    
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
    defaultFavIconPath = '/static/images/favicon.png'
    
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
        iclickchronicle.IClickRecorder(store).ignoreVisit(visit)
        # rewind to the first page, to reflect changes
        return self.updateTable(ctx, self.startPage,
                                self.defaultItemsPerPage)

    def trimTitle(self, visitDict):
        title = visitDict['title']
        if self.maxTitleLength < len(title):
            visitDict['title'] = '%s...' % title[:self.maxTitleLength - 3]
        return visitDict

    def prepareVisited(self, visited):
        visited = iclickchronicle.IVisited(visited)
        desc = visited.asDict()
        favIcon = visited.asIcon()
        if favIcon is None:
            iconPath = self.defaultFavIconPath
        else:
            iconPath = '/%s' % favIcon.prefixURL
        desc['icon'] = iconPath
        return self.trimTitle(desc)
        

class ClickChronicleBenefactor(Item):
    '''i am responsible for granting priveleges to avatars,
       which equates to installing stuff in their store'''

    implements(ixmantissa.IBenefactor)
    typeName = 'clickchronicle_benefactor'
    schemaVersion = 1

    endowed = attributes.integer(default = 0)

    def endow(self, ticket, avatar):
        self.endowed += 1

        avatar.findOrCreate(website.WebSite).installOn(avatar)
        avatar.findOrCreate(webapp.PrivateApplication,
                            preferredTheme=u'cc-skin').installOn(avatar)
        avatar.findOrCreate(ClickChronicleInitializer).installOn(avatar)

class ClickChronicleInitializer(Item):
    """
    Installed by the Click Chronicle benefactor, this Item presents
    itself as a page for initializing your password.  Once done, the
    actual ClickChronicle powerups are installed.
    """
    implements(ixmantissa.INavigableElement)

    typeName = 'clickchronicle_password_initializer'
    schemaVersion = 1

    installedOn = attributes.reference()

    def installOn(self, other):
        assert self.installedOn is None, "Cannot install ClickChronicleInitializer on more than one thing"
        other.powerUp(self, ixmantissa.INavigableElement)
        self.installedOn = other

    def getTabs(self):
        # This won't ever actually show up
        return [webnav.Tab('Preferences', self.storeID, 1.0)]

    def topPanelContent(self):
        return None

    def setPassword(self, password):
        """
        Set the password for this user, install the ClickChronicle
        powerups and delete this Item from the database.
        """
        substore = self.store.parent.getItemByID(self.store.idInParent)
        for acc in self.store.parent.query(userbase.LoginAccount,
                                           userbase.LoginAccount.avatars == substore):
            acc.password = password
            self._reallyEndow()
            return

    def _reallyEndow(self):
        avatar = self.installedOn

        for item in (ClickList, DomainList, Preferences,
                     ClickRecorder, indexinghelp.SyncIndexer,
                     SearchBox, AuthenticationApplication):
            avatar.findOrCreate(item).installOn(avatar)

        avatar.powerDown(self, ixmantissa.INavigableElement)
        self.deleteFromStore()


class ClickChronicleInitializerPage(rend.Page):
    docFactory = loaders.xmlfile(util.sibpath(__file__, 'static/html/initialize.html'))

    def renderHTTP(self, ctx):
        req = inevow.IRequest(ctx)
        password = req.args.get('password', [None])[0]

        if password is None:
            return rend.Page.renderHTTP(self, ctx)

        self.original.store.transact(self.original.setPassword, password)
        return URL.fromString('/')

registerAdapter(ClickChronicleInitializerPage,
                ClickChronicleInitializer,
                inevow.IResource)


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
            yield self.prepareVisited(v)

    def countTotalItems(self, ctx):
        return iclickchronicle.IClickRecorder(self.original.store).visitCount

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

            yield self.prepareVisited(v)

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

class ClickRecorder(Item, website.PrefixURLMixin):
    """
    I exist independently of the rest of the application and accept
    HTTP requests at private/record, which i farm off to URLGrabber.
    """
    schemaVersion = 1
    implements(ixmantissa.ISiteRootPlugin, iclickchronicle.IClickRecorder)
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
    installedOn = attributes.reference()

    def installOn(self, other):
        assert self.installedOn is None, "Cannot install ClickRecorder on more than one thing"
        super(ClickRecorder, self).installOn(other)
        other.powerUp(self, iclickchronicle.IClickRecorder)
        self.installedOn = other

    def activate(self):
        self.bookmarkVisit = self.store.findOrCreate(BookmarkVisit)

    def createResource(self):
        return URLGrabber(self)

    def recordClick(self, qargs, index=True, storeFavicon=True):
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
                                                   referrer, index=index,
                                                   storeFavicon=storeFavicon)
            return futureSuccess.addCallback(lambda ign: forget())

        ref = qargs.get('ref')

        if ref:
            # we got some value for "ref".  pass the referrer url to
            # findOrCreateVisit, using same for title, because on the
            # off chance that we didn't record the click when the user
            # was viewing the referrer page, we don't have much else
            # meaningful to use
            deferred = self.findOrCreateVisit(ref, ref, index=index, 
                                              storeFavicon=storeFavicon)
            deferred.addCallback(storeReferee)
        else:
            # Most likely selected a bookmark/shortcut
            deferred = storeReferee(self.bookmarkVisit)

        return deferred

    def fetchFavicon(self, domain):
        def gotFavicon(data):
            s = self.installedOn
            def txn():
                for ctype in factory.response_headers.get('content-type', ()):
                    break
                else:
                    ctype = 'image/x-icon'
            
                fi = FavIcon(prefixURL='private/icons/%s.ico' % domain.host, 
                             data=data, contentType=ctype, store=s)
                fi.installOn(s)
                domain.favIcon = fi
            s.transact(txn)

        url = str(URL(netloc=domain.host, pathsegs=('favicon.ico',)))
        (host, port) = client._parse(url)[1:-1]
        factory = client.HTTPClientFactory(url)
        reactor.connectTCP(host, port, factory)
        
        return factory.deferred.addCallbacks(gotFavicon, lambda ign: None)
        
    def findOrCreateVisit(self, url, title, referrer=None, index=True, storeFavicon=True):
        """
        Try to find a visit to the same url TODAY.
        If found update the timestamp and return it.
        Otherwise create a new Visit.
        """
        host = URL.fromString(url).netloc
        domain = self.store.findOrCreate(Domain, host=host, title=host)
        if domain.ignore:
            return
        if domain.favIcon is None and storeFavicon:
            futureFavicon = self.fetchFavicon(domain)
        else:
            futureFavicon = defer.succeed(None)
            
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
            return futureFavicon.addCallback(lambda ign: self.store.transact(_))

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
            futureSuccess = self.rememberVisit(visit)
        else:
            futureSuccess = defer.succeed(None)
            
        futureVisit = defer.gatherResults((futureFavicon, futureSuccess))
        return futureVisit.addBoth(lambda ign: visit)

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
        indexer = iclickchronicle.IIndexer(self.store)
        d=indexer.index(visit)
        if self.caching:
            d.addCallback(cbCachePage)
        return d

    def forgetVisit(self, visit):
        indexer = iclickchronicle.IIndexer(self.store)
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
            yield self.prepareVisited(iclickchronicle.IVisited(visit))

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

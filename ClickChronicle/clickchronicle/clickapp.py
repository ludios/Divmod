from datetime import datetime, timedelta
from zope.interface import implements

from twisted.python.components import registerAdapter
from nevow.url import URL
from nevow import rend, inevow, tags

from epsilon.extime import Time

from axiom.item import Item
from axiom import attributes

from xmantissa import ixmantissa, webnav, website, webapp

from clickchronicle import indexinghelp
from clickchronicle.util import PagedTableMixin
from clickchronicle.visit import Visit, Domain
from clickchronicle.searchparser import parseSearchString

class SearchBox(Item):
    implements(ixmantissa.INavigableElement)
    typeName = 'clickchronicle_searchbox'
    schemaVersion = 1

    searchPattern = attributes.inmemory()
    formAction = attributes.inmemory()

    searches = attributes.integer(default=0)

    def installOn(self, other):
        other.powerUp(self, ixmantissa.INavigableElement)

    def activate(self):
        (privApp,) = list(self.store.query(webapp.PrivateApplication))
        docFactory = privApp.getDocFactory('search-box-fragment')
        self.searchPattern = inevow.IQ(docFactory).patternGenerator('search')
        (searcher,) = list(self.store.query(ClickSearcher))
        self.formAction = privApp.linkTo(searcher.storeID)
    
    def topPanelContent(self):
        return self.searchPattern.fillSlots('action', self.formAction)

    def getTabs(self):
        return []
        
class CCPagedTableMixin(PagedTableMixin):
    maxTitleLength = 70

    def makeScriptTag(self, src):
        return tags.script(type='application/x-javascript', 
                           src=src)
    def head(self):
        return self.makeScriptTag('/static/js/paged-table.js')

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
        webapp.PrivateApplication(store = avatar, 
                                  preferredTheme = u'cc-skin').installOn(avatar)

        for item in (website.WebSite, ClickList, Preferences,
                     ClickRecorder, indexinghelp.SyncIndexer,
                     ClickSearcher, SearchBox):
            
            item(store=avatar).installOn(avatar)

class ClickList(Item):
    """similar to Preferences, i am an implementor of INavigableElement,
       and PrivateApplication will find me when when it looks in the user's
       store"""
       
    implements(ixmantissa.INavigableElement)
    typeName = 'clickchronicle_clicklist'
    clicks = attributes.integer(default = 0)
    schemaVersion = 1

    def installOn(self, other):
        other.powerUp(self, ixmantissa.INavigableElement)

    def getTabs(self):
        '''show a link to myself in the navbar'''
        return [webnav.Tab('My Clicks', self.storeID, 0.2)]

    def topPanelContent(self):
        return None

class ClickListFragment(rend.Fragment, CCPagedTableMixin):
    '''i adapt ClickList to INavigableFragment'''
    
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
        return self.original.clicks
        
registerAdapter(ClickListFragment, 
                ClickList,
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
    implements(ixmantissa.ISiteRootPlugin)
    typeName = 'clickchronicle_clickrecorder'
    urlCount = attributes.integer(default = 0)
    prefixURL = 'private/record'
    # Caching needs to be provisioned/bestowed
    caching = True
    # Number of MRU visits to keep
    maxCount = 500

    def installOn(self, other):
        other.powerUp(self, ixmantissa.ISiteRootPlugin)

    def createResource(self):
        return URLGrabber(self)

    def recordClick(self, qargs):
        """
        Extract POST arguments and create a Visit object before indexing and caching.
        """
        
        if self.urlCount > self.maxCount:
            self.forgetOldestVisit()
        url = qargs.get('url')
        if url is None:
            # No url, no deal.
            return
        title = qargs.get('title')
        if not title or title.isspace():
            title = url
        visit = self.findOrCreateVisit(url, title)
        
    def findOrCreateVisit(self, url, title):
        """
        Try to find a visit to the same url TODAY.
        If found update the timestamp and return it.
        Otherwise create a new Visit.
        """
        domainStr = URL.fromString(url).netloc
        domain = self.store.findOrCreate(Domain, url=domainStr, title=domainStr)
        if domain and domain.ignore:
            return
        existingVisit = self.findVisitForToday(url)
        timeNow = Time.fromDatetime(datetime.now())
        
        if existingVisit:
            # Already visited today
            def _():
                existingVisit.timestamp = timeNow
                existingVisit.visitCount += 1
                existingVisit.domain.visitCount += 1
                return existingVisit
            visit = self.store.transact(_)
        else:
            # New visit today
            def _():
                visit = Visit(store = self.store,
                              url = url,
                              timestamp = timeNow,
                              title = title,
                              domain = domain)
                (clickList,) = list(self.store.query(ClickList))
                clickList.clicks += 1
                self.urlCount += 1
                visit.visitCount += 1
                visit.domain.visitCount +=1
                return visit
            visit = self.store.transact(_)
            self.postProcess(visit)

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

    def postProcess(self, visit):
        def cbCachePage(doc):
            visit.cachePage(doc.source)
        indexer = indexinghelp.IIndexer(self.store)
        d=indexer.index(visit)
        if self.caching:
            d.addCallback(cbCachePage)

    def forgetOldestVisit(self):
        """
        Remove oldest Visit from the store, cache and index.
        """
        # XXX - This needs to be more sophisticated since there is a known race
        # condition for a Visit being deleted from the index before the page has
        # been fetched and indexed/cahced
        def _():
            for visit in self.store.query(Visit, sort=Visit.timestamp.ascending):
                break
            print 'deleting visit %s' % visit.storeID
            indexer = indexinghelp.IIndexer(self.store)
            indexer.delete(visit)
            visit.forget()
            visit.deleteFromStore()
            self.urlCount -= 1
        self.store.transact(_)

    
class SearchClicks(rend.Fragment, CCPagedTableMixin):
    fragmentName = 'search-fragment'
    title = ''
    live = True
    
    discriminator = None
    matchingClicks = 0
    
    def __init__(self, orig, docFactory=None):
        (self.indexer,) = list(orig.store.query(indexinghelp.SyncIndexer))
        (self.searchbox,) = list(orig.store.query(SearchBox))
        rend.Fragment.__init__(self, orig, docFactory)

    def head(self):
        yield self.makeScriptTag('/static/js/search.js')
        yield CCPagedTableMixin.head(self)

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
        CCPagedTableMixin.goingLive(self, ctx, client)

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
            (visit,) = list(store.query(Visit, Visit.storeID == spec['uid']))
            yield self.trimTitle(visit.asDict())

    def incrementSearches(self):
        def txn(): 
            self.searchbox.searches += 1
        self.original.store.transact(txn)
                    
class ClickSearcher(Item):
    implements(ixmantissa.INavigableElement)
    typeName = 'clickchronicle_clicksearcher'
    schemaVersion = 1

    searches = attributes.integer(default = 0)

    def installOn(self, other):
        other.powerUp(self, ixmantissa.INavigableElement)

    def topPanelContent(self):
        return None

    def getTabs(self):
        return []

registerAdapter(SearchClicks,
                ClickSearcher,
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

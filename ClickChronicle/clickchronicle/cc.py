from __future__ import division
from axiom.item import Item
from axiom import attributes
from zope.interface import implements
from xmantissa.webnav import Tab
from xmantissa import ixmantissa
from xmantissa.webadmin import ParentCounterMixin
from nevow import loaders, rend, livepage, inevow
from twisted.python.components import registerAdapter
from xmantissa.webadmin import WebSite, PrivateApplication
from xmantissa.website import PrefixURLMixin
from epsilon.extime import Time
from datetime import datetime, timedelta
from twisted.python.util import sibpath
from clickchronicle.indexinghelp import (IIndexable, IIndexer, SyncIndexer, 
                                         makeDocument, getPageSource)
from clickchronicle.searchparser import parseSearchString
from nevow import livepage, tags, inevow
from math import ceil
from nevow.url import URL

class Domain(Item):
    name = attributes.bytes()
    title = attributes.bytes()
    visitCount = attributes.integer(default=0)

    schemaVersion = 1
    typeName = 'domain'

    
class Visit(Item):
    """I correspond to a webpage-visit logged by a clickchronicle user"""
    implements(IIndexable)
    timestamp = attributes.timestamp()
    url = attributes.bytes()
    title = attributes.bytes()
    visitCount = attributes.integer(default=1)
    domain = attributes.reference(allowNone = False)

    schemaVersion = 1
    typeName = 'visit'

    
    def asDocument(self):
        """
        Return a Document in a Deferred.
        """
        def cbGotSource(pageSource):
            doc = makeDocument(self, pageSource)
            return doc
        d = getPageSource(self.url)
        d.addCallback(cbGotSource)
        return d

    def asDict(self):
        """Return a friendly dictionary of url/title/timestamp"""
        return dict(url = self.url, title = self.title,
                    timestamp = self.timestamp.asHumanly(), visits=self.visitCount)
        
    def cachePage(self, pageSource):
        """
        Cache the source for this Visit.
        """
        newFile = self.store.newFile(self.cachedFileName())
        newFile.write(pageSource)
        newFile.close()

    def cachedFileName(self):
        """
        Return the path to the cached source for this visit.
        The path consists of the iso date for the visit as directory and the
        storeID as the filename.
        e.g. cchronicle.axiom/files/account/test.com/user/files/cache/2005-09-10/55.html
        """
        # XXX - I doubt that this is how these path objects are supposed to
        # be manipulated. Check for sanity/style.
        dirName = self.timestamp.asDatetime().date().isoformat()
        cacheDir = self.store.newDirectory('cache/%s' % dirName)
        fileName = str(cacheDir.path)+ '/' + str(self.storeID) + '.html'
        return fileName

    def forget(self):
        import os
        fName = self.cachedFileName()
        os.remove(fName)

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

    def getTabs( self ):
        return [Tab('Preferences', self.storeID, 0.0)]


class PreferencesFragment( rend.Fragment ):
    """I will get an adapter for Preferences instances, who
       implements INavigableFragment"""
       
    fragmentName = 'preferences-fragment'
    title = ''
    live = True

    def head( self ):
        return None

    def data_preferences( self, ctx, data ):
        """return a dict of self.original's (Preferences instance) columns"""
        return dict( displayName = self.original.displayName,
                     homepage = self.original.homepage )

registerAdapter( PreferencesFragment,
                 Preferences,
                 ixmantissa.INavigableFragment )

class ClickList( Item ):
    """similar to Preferences, i am an implementor of INavigableElement,
       and PrivateApplication will find me when when it looks in the user's
       store"""
       
    implements( ixmantissa.INavigableElement )
    typeName = 'clickchronicle_clicklist'
    clicks = attributes.integer( default = 0 )
    schemaVersion = 1

    def installOn(self, other):
        other.powerUp( self, ixmantissa.INavigableElement )

    def getTabs( self ):
        '''show a link to myself in the navbar'''
        return [Tab('My Clicks', self.storeID, 0.2)]

class PagedTableMixin:
    itemsPerPage = (10, 20, 50, 100)
    defaultItemsPerPage = 10
    startPage = 1
    
    def data_totalItems( self, ctx, data ):
        return self.countTotalItems(ctx)

    def data_itemsPerPage( self, ctx, data ):
        return self.itemsPerPage
   
    def handle_updateTable( self, ctx, pageNumber, itemsPerPage ):
        yield (self.updateTable(ctx, pageNumber, itemsPerPage), livepage.eol)
        yield (self.changeItemsPerPage(ctx, pageNumber, itemsPerPage), livepage.eol)

    def updateTable(self, ctx, pageNumber, itemsPerPage):
        (pageNumber, itemsPerPage) = (int(pageNumber), int(itemsPerPage))
        
        rowDicts = list(self.generateRowDicts(ctx, pageNumber, itemsPerPage))
        tablePattern = inevow.IQ(self.docFactory).onePattern('table')
        
        table = tablePattern(data=rowDicts)
        offset = (pageNumber - 1) * itemsPerPage
        
        yield (livepage.set('tableContainer', table), livepage.eol)
        yield (livepage.set('startItem', offset + 1), livepage.eol)
        yield (livepage.set('endItem', offset + len(rowDicts)), livepage.eol)

    def handle_changeItemsPerPage(self, ctx, pageNumber, perPage):
        yield (self.updateTable(ctx, 1, perPage), livepage.eol)
        yield (self.changeItemsPerPage(ctx, 1, perPage), livepage.eol)
            
    def changeItemsPerPage( self, ctx, pageNumber, perPage ):
        perPage = int(perPage)
        totalItems = self.countTotalItems(ctx)
        pageNumbers = xrange(1, int(ceil(totalItems / perPage))+1)
        pageNumsPatt = inevow.IQ(self.docFactory).onePattern('pagingWidget')
        pagingWidget = pageNumsPatt(data=pageNumbers)
        yield (livepage.set('pagingWidgetContainer', pagingWidget), livepage.eol)
        yield (livepage.js.setCurrentPage(pageNumber), livepage.eol)
    
    def goingLive( self, ctx, client ):
        client.call('setItemsPerPage', self.defaultItemsPerPage)
        client.send(self.updateTable(ctx, self.startPage, self.defaultItemsPerPage))
        client.send(self.changeItemsPerPage(ctx, self.startPage, self.defaultItemsPerPage))

    # override these methods
    def generateRowDicts( self, ctx, pageNumber, itemsPerPage ):
        """I return a sequence of dictionaries that will be used as data for
           the corresponding template's 'table' pattern.

           pageNumber: number of page currently being viewed, starting from 1, not 0"""
                       
        raise NotImplementedError

    def countTotalItems( self, ctx ):
        raise NotImplementedError

class CCPagedTableMixin(PagedTableMixin):
    def makeScriptTag(self, src):
        return tags.script(type='application/x-javascript', 
                           src=src)
    def head(self):
        return self.makeScriptTag('/static/js/paged-table.js')

class ClickListFragment(rend.Fragment, CCPagedTableMixin):
    '''i adapt ClickList to INavigableFragment'''
    
    fragmentName = 'click-list-fragment'
    title = ''
    live = True

    def generateRowDicts( self, ctx, pageNumber, itemsPerPage ):
        store = self.original.store 
        offset = (pageNumber - 1) * itemsPerPage
        
        for v in store.query(Visit, sort = Visit.timestamp.descending,
                             limit = itemsPerPage, offset = offset):
            
            yield v.asDict()

    def countTotalItems(self, ctx):
        return self.original.clicks

registerAdapter( ClickListFragment, 
                 ClickList,
                 ixmantissa.INavigableFragment )

class SearchClicks(Item):
    implements( ixmantissa.INavigableElement )
    typeName = 'clickchronicle_searchclicks'
    searches = attributes.integer( default = 0 )
    schemaVersion = 1

    def installOn(self, other):
        other.powerUp( self, ixmantissa.INavigableElement )

    def getTabs( self ):
        return [Tab('Search Clicks', self.storeID, 0.1)]

class SearchClicksFragment(rend.Fragment, CCPagedTableMixin):
    totalMatches = 0
    discriminator = None

    fragmentName = 'search-clicks-fragment'
    title = ''
    live = True

    def __init__(self, original, docFactory=None):
        rend.Fragment.__init__(self, original, docFactory)
        (self.indexer,) = list(original.store.query(SyncIndexer))

    def countTotalItems(self, ctx):
        return self.totalMatches

    def generateRowDicts(self, ctx, page, itemsPerPage):
        offset = (page - 1) * itemsPerPage
        specs = self.indexer.search(self.discriminator,
                                    startingIndex = offset,
                                    batchSize = itemsPerPage)
        store = self.original.store
        for spec in specs:
            (visit,) = (store.query(Visit, Visit.storeID == spec['uid']))
            yield visit.asDict()

    def goingLive(self, ctx, client):
        # override PagedTableMixin.goingLive, b/c in this case we can't
        # be expected to have any data to display in the paging widget
        # on the initial page load
        pass

    def handle_search(self, ctx, discriminator):
        self.discriminator = ' '.join(parseSearchString(discriminator))
        (estimated, total) = self.indexer.count(self.discriminator)
        self.totalMatches = estimated
        return self.updateTable(ctx, self.startPage,
                                self.defaultItemsPerPage)

registerAdapter(SearchClicksFragment,
                SearchClicks,
                ixmantissa.INavigableFragment)

class URLGrabber(rend.Page):
    """I handle ClickRecorder's HTTP action.  i am not an Item
       because i have a lot of attributes inherited from rend.Page"""
    def __init__( self, recorder ):
        self.recorder = recorder
        
    def renderHTTP( self, ctx ):
        """get url and title GET variables, supplying sane defaults"""
        urlpath = inevow.IRequest( ctx ).URLPath()
        qargs = dict( urlpath.queryList() )
        self.recorder.recordClick(qargs)
        return ''
            
class ClickRecorder( Item, PrefixURLMixin ):
    """
    I exist independently of the rest of the application and accept
    HTTP requests at private/record, which i farm off to URLGrabber.
    """
    schemaVersion = 1
    implements( ixmantissa.ISiteRootPlugin )
    typeName = 'clickrecorder'
    urlCount = attributes.integer( default = 0 )
    prefixURL = 'private/record'
    # Caching needs to be provisioned/bestowed
    caching = True
    # Number of MRU visits to keep
    maxCount = 500

    def installOn(self, other):
        other.powerUp(self, ixmantissa.ISiteRootPlugin)

    def createResource( self ):
        return URLGrabber( self )

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
        dtNow = datetime.now()
        timeNow = Time.fromDatetime(datetime.now())
        todayBegin = dtNow.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrowBegin = (dtNow+timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        existingVisit = None
        for existingVisit in self.store.query(Visit,
                                              attributes.AND(Visit.timestamp >= Time.fromDatetime(todayBegin),
                                                             Visit.timestamp < Time.fromDatetime(tomorrowBegin),
                                                             Visit.url == url)):
            break

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
                self.urlCount += 1
                # Hook up the domain
                domainStr = URL.fromString(url).netloc
                domain = self.store.findOrCreate(Domain, name=domainStr, title=domainStr)
                domain.visitCount +=1 
                visit = Visit(store = self.store,
                              url = url,
                              timestamp = timeNow,
                              title = title,
                              domain = domain)
                visit.domain.visitCount += 1
                (clickList,) = list(self.store.query(ClickList))
                clickList.clicks += 1
                return visit
            visit = self.store.transact(_)
            self.postProcess(visit)

    def postProcess(self, visit):
        def cbCachePage(doc):
            visit.cachePage(doc.source)
        indexer = IIndexer(self.store)
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
            indexer = IIndexer(self.store)
            indexer.delete(visit)
            visit.forget()
            visit.deleteFromStore()
            self.urlCount -= 1
        self.store.transact(_)

 
class ClickChronicleBenefactor( Item ):
    '''i am responsible for granting priveleges to avatars, 
       which equates to installing stuff in their store'''
       
    implements( ixmantissa.IBenefactor )
    typeName = 'clickchronicle_benefactor'
    schemaVersion = 1

    endowed = attributes.integer( default = 0 )

    def endow(self, ticket, avatar):
        self.endowed += 1
        PrivateApplication( store = avatar, 
                            preferredTheme = u'cc-skin' ).installOn(avatar)

        for item in (WebSite, ClickList, SearchClicks,
                     Preferences, ClickRecorder, SyncIndexer):
            
            item(store=avatar).installOn(avatar)
            

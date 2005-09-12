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
from datetime import datetime
from twisted.python.util import sibpath
from clickchronicle.indexinghelp import IIndexable, IIndexer, SyncIndexer, makeDocument, getPageSource
from nevow import livepage, tags, inevow, flat
from math import ceil

class Visit(Item):
    """I correspond to a webpage-visit logged by a clickchronicle user"""
    implements(IIndexable)
    timestamp = attributes.timestamp()
    url = attributes.bytes()
    title = attributes.bytes()

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
        return [Tab('Preferences', self.storeID, 0.2)]


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

class LinkList( Item ):
    """similar to Preferences, i am an implementor of INavigableElement,
       and PrivateApplication will find me when when it looks in the user's
       store"""
       
    implements( ixmantissa.INavigableElement )
    typeName = 'clickchronicle_linklist'
    links = attributes.integer( default = 0 )
    schemaVersion = 1

    def installOn(self, other):
        other.powerUp( self, ixmantissa.INavigableElement )

    def getTabs( self ):
        '''show a link to myself in the navbar'''
        return [Tab('My Clicks', self.storeID, 0.1)]

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

    
class LinkListFragment( rend.Fragment, PagedTableMixin ):
    '''i adapt LinkList to INavigableFragment'''
    
    fragmentName = 'link-list-fragment'
    title = ''
    live = True
    
    def head( self ):
        return tags.script(type='application/x-javascript', 
                           src='/static/js/link-list-fragment.js')

    def generateRowDicts( self, ctx, pageNumber, itemsPerPage ):
        store = self.original.store 
        offset = (pageNumber - 1) * itemsPerPage
        
        for v in store.query(Visit, sort = Visit.timestamp.descending,
                             limit = itemsPerPage, offset = offset):
            
            yield dict(url = v.url, 
                       timestamp = v.timestamp.asHumanly(),
                       title = v.title)

    def countTotalItems(self, ctx):
        return self.original.links

registerAdapter( LinkListFragment, 
                 LinkList,
                 ixmantissa.INavigableFragment )

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
            print 'url is None'
            return
        title = qargs.get('title', 'Untitled')
        if not title:
            title = url
        timeNow = Time.fromDatetime(datetime.now())
        def _():
            self.urlCount += 1
            visit = Visit(store = self.store,
                  url = url,
                  timestamp = timeNow,
                  title = title)
            (linkList,) = list(self.store.query(LinkList))
            linkList.links += 1
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

        for item in (WebSite, LinkList, Preferences, ClickRecorder, SyncIndexer):
            item(store=avatar ).installOn(avatar)
            

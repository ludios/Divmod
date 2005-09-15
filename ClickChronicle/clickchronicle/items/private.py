from datetime import datetime, timedelta
from zope.interface import implements

from twisted.python.components import registerAdapter
from nevow.url import URL

from epsilon.extime import Time

from axiom.item import Item
from axiom import attributes

from xmantissa import ixmantissa, webnav, website, webapp

from clickchronicle import resources, indexinghelp
from clickchronicle.items.common import Visit, Domain

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
                     ClickRecorder, indexinghelp.SyncIndexer):
            
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

registerAdapter(resources.ClickListFragment, 
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

registerAdapter(resources.PreferencesFragment,
                Preferences,
                ixmantissa.INavigableFragment)

class ClickRecorder(Item, website.PrefixURLMixin):
    """
    I exist independently of the rest of the application and accept
    HTTP requests at private/record, which i farm off to URLGrabber.
    """
    schemaVersion = 1
    implements(ixmantissa.ISiteRootPlugin)
    typeName = 'clickrecorder'
    urlCount = attributes.integer(default = 0)
    prefixURL = 'private/record'
    # Caching needs to be provisioned/bestowed
    caching = True
    # Number of MRU visits to keep
    maxCount = 500

    def installOn(self, other):
        other.powerUp(self, ixmantissa.ISiteRootPlugin)

    def createResource(self):
        return resources.URLGrabber(self)

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

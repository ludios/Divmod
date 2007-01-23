# -*- test-case-name: clickchronicle.test.test_clickapp -*-

import pytz

from datetime import timedelta
from zope.interface import implements

from twisted.web.util import redirectTo
from twisted.python.filepath import FilePath
from twisted.cred import portal
from twisted.python.components import registerAdapter
from twisted.internet import defer

from nevow.url import URL
from nevow import rend, inevow, tags, flat, entities, athena, loaders
from nevow.athena import expose

from epsilon.extime import Time

from axiom.item import Item, declareLegacyItem
from axiom import upgrade, userbase, scheduler, attributes, errors
from axiom.tags import Catalog, Tag
from axiom.dependency import dependsOn

from vertex import q2q

from xmantissa import ixmantissa, webnav, website, webapp, prefs, tdbview, sharing, liveform
from xmantissa.webtheme import getLoader

from clickchronicle import iclickchronicle, indexinghelp, clickbrowser
from clickchronicle.util import makeStaticURL
from clickchronicle.visit import Visit, Domain, BookmarkVisit, Bookmark
from clickchronicle.searchparser import parseSearchString
from clickchronicle.publicpage import AGGREGATION_PROTOCOL, ONLY_INCREMENT
from clickchronicle.publicpage import AggregateClick

from xapwrap.index import NoIndexValueFound

flat.registerFlattener(lambda t, ign: t.asHumanly(), Time)


class ClickChronicleBenefactor(Item):
    '''i am responsible for granting priveleges to avatars,
       which equates to installing stuff in their store'''
    implements(ixmantissa.IBenefactor)

    typeName = 'clickchronicle_benefactor'
    schemaVersion = 2

    # Number of users this benefactor has endowed
    endowed = attributes.integer(default = 0)

    # Max number of clicks users endowed by this benefactor will be
    # able to store.
    maxClicks = attributes.integer(default=1000)


def benefactor1To2(oldBene):
    newBene = oldBene.upgradeVersion(
        'clickchronicle_benefactor', 1, 2,
        endowed=oldBene.endowed,
        maxClicks=1000)
    return newBene
upgrade.registerUpgrader(benefactor1To2, 'clickchronicle_benefactor', 1, 2)

class ClickList(Item):
    """similar to Preferences, i am an implementor of INavigableElement,
       and PrivateApplication will find me when when it looks in the user's
       store"""

    implements(ixmantissa.INavigableElement,
               iclickchronicle.IClickList)
    typeName = 'clickchronicle_clicklist'
    schemaVersion = 1

    installedOn = attributes.reference()
    clicks = attributes.integer(default = 0)

    powerupInterfaces = (ixmantissa.INavigableElement,)

    def getTabs(self):
        """show a link to myself in the navbar"""
        return [webnav.Tab('Clicks', self.storeID, 0.9)]

    allowedActions = (clickbrowser.bookmarkAction,
         clickbrowser.ignoreVisitAction,
         clickbrowser.privateVisitToggleAction,
         clickbrowser.deleteAction)



class CCPreferenceCollection(Item, prefs.PreferenceCollectionMixin):
    implements(ixmantissa.IPreferenceCollection)

    schemaVersion = 3
    typeName = 'clickchronicle_preference_collection'
    collectionName = 'ClickChronicle'

    shareClicks = attributes.boolean(default=True)

    clicklist = dependsOn(ClickList)
    powerupInterfaces = (ixmantissa.IPreferenceCollection,)

    def publicPage():
        def get(self):
            # figure out if we've shared this before...
            try:
                sharing.getShare(self.store,
                                 sharing.getEveryoneRole(self.store),
                                 shareID=u'clicks')
                return True
            except sharing.NoSuchShare:
                return False

        def set(self, value):
            if value:
                sharing.shareItem(
                        self.clicklist,
                        shareID=u'clicks',
                        toRole=sharing.getEveryoneRole(self.store))
            else:
                sharing.unShare(self.clicklist)
        return get, set
    publicPage = property(*publicPage())


    def getPreferenceParameters(self):
        return (liveform.Parameter('shareClicks',
                                   liveform.CHECKBOX_INPUT,
                                   bool,
                                   'Share Clicks'),
                liveform.Parameter('publicPage',
                                   liveform.CHECKBOX_INPUT,
                                   bool,
                                   'Give Me A Public Page'))

    def getSections(self):
        return None

    def getTabs(self):
        return (webnav.Tab('ClickChronicle', self.storeID, 0.0),)

def ccPreferenceCollection1To2(old):
    return old.upgradeVersion('clickchronicle_preference_collection', 1, 2,
                              installedOn=old.installedOn,
                              shareClicks=old.shareClicks)

def ccPreferenceCollection2to3(old):
    return old.upgradeVersion('clickchronicle_preference_collection', 2, 3,
                              clicklist=old.store.findOrCreate(ClickList),
                              shareClicks=old.shareClicks)

declareLegacyItem('clickchronicle_preference_collection', 2,
                  dict(installedOn=attributes.reference(),
                       shareClicks=attributes.boolean()))
upgrade.registerUpgrader(ccPreferenceCollection1To2, 'clickchronicle_preference_collection', 1, 2)
upgrade.registerUpgrader(ccPreferenceCollection2to3, 'clickchronicle_preference_collection', 2, 3)

class ClickChronicleInitializer(Item):
    """
    Installed by the Click Chronicle benefactor, this Item presents
    itself as a page for initializing your password.  Once done, the
    actual ClickChronicle powerups are installed.
    """
    implements(ixmantissa.INavigableElement)

    typeName = 'clickchronicle_password_initializer'
    schemaVersion = 3

    installedOn = attributes.reference()
    maxClicks = attributes.integer()

    powerupInterfaces = (ixmantissa.INavigableElement,)

    def getTabs(self):
        # This won't ever actually show up
        return [webnav.Tab('Preferences', self.storeID, 1.0)]

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

def initializer1To2(oldInit):
    newInit = oldInit.upgradeVersion(
        'clickchronicle_password_initializer', 1, 2,
        installedOn=oldInit.installedOn,
        maxClicks=oldInit.maxClicks)
    return newInit

def initializer2To3(oldInit):
    newInit = oldInit.upgradeVersion(oldInit.typeName, 2, 3)
    newInit.store.powerDown(newInit, ixmantissa.INavigableElement)
    newInit.deleteFromStore()

declareLegacyItem('clickchronicle_password_initializer', 2,
                  dict(installedOn=attributes.reference(),
                       maxClicks=attributes.integer()))

upgrade.registerUpgrader(initializer1To2, 'clickchronicle_password_initializer', 1, 2)
upgrade.registerUpgrader(initializer2To3, 'clickchronicle_password_initializer', 2, 3)


class DomainList(Item):
    """similar to Preferences, i am an implementor of INavigableElement,
       and PrivateApplication will find me when when it looks in the user's
       store"""

    implements(ixmantissa.INavigableElement)
    typeName = 'clickchronicle_domainlist'
    schemaVersion = 1

    installedOn = attributes.reference()
    clicks = attributes.integer(default = 0)
    powerupInterfaces = (ixmantissa.INavigableElement,)

    def getTabs(self):
        '''show a link to myself in the navbar'''
        return [webnav.Tab('Domains', self.storeID, 0.8)]

class BlockedDomainList(Item):
    implements(ixmantissa.INavigableElement)
    typeName = 'clickchronicle_blocked_domain_list'
    schemaVersion = 1

    installedOn = attributes.reference()
    powerupInterfaces = (ixmantissa.INavigableElement,)

    def getTabs(self):
        return [webnav.Tab('Filtered Domains', self.storeID, 0.7)]

class ClickListFragment(tdbview.TabularDataView):
    '''i adapt ClickList to INavigableFragment'''

    def __init__(self, original):
        # will probably have to do something wacky in order to emulate
        # clickchronicle's method of displaying visit information in
        # the tdb
        self.clickListItem = original
        (tdm, views) = clickbrowser.makeClickTDM(original.store, Visit)
        allowedActions = self.getAllowedActions()
        tdbview.TabularDataView.__init__(self, tdm, views, allowedActions, width='100%')

    def getAllowedActions(self):
        return getattr(self.clickListItem, 'allowedActions', ())


    def customizeFor(self, forUser):
        # Hmm, this method probably shouldn't be required, but currently the
        # sharing system invokes it unconditionally... remove me if that
        # changes
        return self

registerAdapter(ClickListFragment,
                iclickchronicle.IClickList,
                ixmantissa.INavigableFragment)

class BookmarkList(Item):
    """similar to Preferences, i am an implementor of INavigableElement,
       and PrivateApplication will find me when when it looks in the user's
       store"""

    implements(ixmantissa.INavigableElement)
    typeName = 'clickchronicle_bookmarklist'
    schemaVersion = 1

    installedOn = attributes.reference()
    clicks = attributes.integer(default = 0)
    powerupInterfaces = (ixmantissa.INavigableElement,)

    def getTabs(self):
        '''show a link to myself in the navbar'''
        return [webnav.Tab('Bookmarks', self.storeID, 0.6)]

class BookmarkListFragment(athena.LiveFragment):
    '''i adapt BookmarkList to INavigableFragment'''
    implements(ixmantissa.INavigableFragment)
    _bookmarkTDB = None

    jsClass = u'ClickChronicle.BookmarkList'
    fragmentName = 'bookmark-list'
    live = 'athena'

    magicWord = u'-- All --'

    def filterBookmarks(self, tag):
        if tag == self.magicWord:
            comparison = None
        else:
            comparison = attributes.AND(Tag.object == Bookmark.storeID,
                                        Tag.name == tag)

        self.bookmarkTDB.original.baseComparison = comparison
        self.bookmarkTDB.original.firstPage()
        return self.bookmarkTDB.replaceTable()
    expose(filterBookmarks)

    def getBookmarkTDB(self):
        if self._bookmarkTDB is None:
            (tdm, views) = clickbrowser.makeClickTDM(self.original.store, Bookmark)
            tdv = tdbview.TabularDataView(tdm, views,
                                          (clickbrowser.ignoreVisitAction,
                                           clickbrowser.privateVisitToggleAction,
                                           clickbrowser.deleteAction),
                                          width='100%')
            tdv.docFactory = getLoader(tdv.fragmentName)
            tdv.setFragmentParent(self)
            self._bookmarkTDB = tdv
        return self._bookmarkTDB

    bookmarkTDB = property(getBookmarkTDB)

    def render_bookmarkTDB(self, ctx, data):
        return self.bookmarkTDB

    def render_tagList(self, ctx, data):
        tags = self.original.store.query(Tag, Tag.object == Bookmark.storeID)
        tags = list(tags.getColumn('name').distinct())
        tags = [self.magicWord] + tags

        iq = inevow.IQ(self.docFactory)
        tagListPattern = iq.onePattern('tag-list')
        tagPattern = iq.patternGenerator('tag')

        try:
            tagStan = list(tagPattern.fillSlots('name', name) for name in tags)
        except errors.SQLError:
            return ctx.tag

        return tagListPattern.fillSlots('tags', tagStan)

    def head(self):
        return None

registerAdapter(BookmarkListFragment,
                BookmarkList,
                ixmantissa.INavigableFragment)

class DomainListFragment(tdbview.TabularDataView):
    '''i adapt DomainList to INavigableFragment'''

    def __init__(self, original):
        (tdm, views) = clickbrowser.makeClickTDM(original.store, Domain)

        tdbview.TabularDataView.__init__(self, tdm, views,
                (clickbrowser.bookmarkAction,
                 clickbrowser.blockDomainToggleAction,
                 clickbrowser.privateToggleAction,
                 clickbrowser.deleteAction),
                width='100%')

registerAdapter(DomainListFragment,
                DomainList,
                ixmantissa.INavigableFragment)

class BlockedDomainListFragment(tdbview.TabularDataView):
    def __init__(self, blockedDomainList):
        self.blockedDomainList = blockedDomainList
        (tdm, views) = clickbrowser.makeClickTDM(blockedDomainList.store,
                                                 Domain,
                                                 attributes.OR(Domain.ignore==True,
                                                               Domain.private==True))
        tdbview.TabularDataView.__init__(self, tdm, views,
                (clickbrowser.bookmarkAction,
                 clickbrowser.blockDomainToggleAction,
                 clickbrowser.privateToggleAction),
                width='100%')

registerAdapter(BlockedDomainListFragment,
                BlockedDomainList,
                ixmantissa.INavigableFragment)

class GetExtension(Item):
    implements(ixmantissa.INavigableElement)
    typeName = 'clickchronicle_get_extension'
    schemaVersion = 1

    installedOn = attributes.reference()
    powerupInterfaces = (ixmantissa.INavigableElement,)

    def getTabs(self):
        return [webnav.Tab('Get Extension', self.storeID, 0.5)]

class GetExtensionFragment(rend.Fragment):
    implements(ixmantissa.INavigableFragment)

    fragmentName = 'get-extension-fragment'
    live = False
    title = 'Get Extension'

    def head(self):
        return None

registerAdapter(GetExtensionFragment,
                GetExtension,
                ixmantissa.INavigableFragment)

def sendToPublicPage(senderAvatar, toAddress, protocol, message):
    # Haha it is a message passing system
    assert toAddress.resource == "clickchronicle"
    assert toAddress.domain == "clickchronicle.com"
    assert protocol == AGGREGATION_PROTOCOL
    assert isinstance(message, AggregateClick)

    realm = portal.IRealm(senderAvatar.store.parent)
    # FIXME argh.
    for creds in ((u'ClickChronicle', None), (u'clickchronicle', u'clickchronicle.com')):
        recip = realm.accountByAddress(*creds)
        pp = ixmantissa.IPublicPage(recip, None)
        if pp is not None:
            pp.observeClick(message.structured['title'], message.structured['url'])
            break
    else:
        assert False, 'shock horror. cannot find a system user'

class StaticShellContent(Item):
    implements(ixmantissa.IStaticShellContent)

    schemaVersion = 2
    typeName = 'clickchronicle_static_shell_content'

    installedOn = attributes.reference()
    powerupInterfaces = (ixmantissa.IStaticShellContent,)

    def getHeader(self):
        return tags.a(href="/")[tags.img(border=0, src=makeStaticURL("images/logo.png"))]

    def getFooter(self):
        return (entities.copy, "Divmod 2005")

class CCSearchProvider(Item):
    implements(ixmantissa.ISearchProvider)
    installedOn = attributes.reference()
    schemaVersion = 1
    typeName = 'clickchronicle_search_provider'

    indexer = attributes.inmemory()
    powerupInterfaces = (ixmantissa.ISearchProvider,)

    def activate(self):
        self.indexer = None

    def _cachePowerups(self):
        self.indexer = iclickchronicle.IIndexer(self.installedOn)

    def count(self, term):
        if self.indexer is None:
            self._cachePowerups()

        term = ' '.join(parseSearchString(term))
        (estimated, total) = self.indexer.count(term)
        return defer.succeed(estimated)

    def _syncSearch(self, term, count, offset):
        if self.indexer is None:
            self._cachePowerups()

        term = ' '.join(parseSearchString(term))

        doSearch = lambda **k: self.indexer.search(str(term), startingIndex=offset,
                                                   batchSize=count, **k)

        # this try/except is for compatability with indices created before
        # we started storing a Value with the key "summary".  if a user
        # with such a index does a search, and xapwrap explodes, we'll do
        # the search again, and wont ask for the summary key.  this will
        # be a non-issue once said user records a click

        try:
            specs = doSearch(valuesWanted=('summary','_STOREID'))
        except NoIndexValueFound:
            specs = doSearch()

        for spec in specs:
            visit = self.store.getItemByID(int(spec['values']['_STOREID']))
            yield dict(description=visit.title, url=visit.url,
                       summary=spec.get('values', dict()).get('summary', ''),
                       timestamp=visit.timestamp,
                       score=spec['score'] / 100.0)


    def _wrapResults(self, results):
        class Results(athena.LiveFragment):
            docFactory = loaders.stan(
                            tags.ul[
                                list(
                                    tags.li[
                                        tags.a(href=d['url'])[d['url']]]
                                    for d in results)])
        return Results()

    def search(self, term, keywords, count, offset):
        return defer.succeed(self._wrapResults(self._syncSearch(term, count, offset)))


class ClickRecorder(Item, website.PrefixURLMixin):
    """
    I exist independently of the rest of the application and accept
    HTTP requests at private/record, which i farm off to URLGrabber.
    """
    implements(ixmantissa.ISiteRootPlugin, iclickchronicle.IClickRecorder)

    typeName = 'clickchronicle_clickrecorder'
    schemaVersion = 2

    sessioned = True
    prefixURL = 'private/record'

    privateApplication = dependsOn(webapp.PrivateApplication)
    scheduler = dependsOn(scheduler.SubScheduler)
    shell = dependsOn(StaticShellContent)

    #all the UI bits
    clickList = dependsOn(ClickList)
    blockedDomainList = dependsOn(BlockedDomainList)
    domainList = dependsOn(DomainList)
    indexer = dependsOn(indexinghelp.SyncIndexer)
    bookmarkList = dependsOn(BookmarkList)
    searchProvider = dependsOn(CCSearchProvider)
    cacheManager = dependsOn(indexinghelp.CacheManager)
    getExtension = dependsOn(GetExtension)
    prefs = dependsOn(CCPreferenceCollection)

    # Total number of clicks we have ever received
    clickCount = attributes.integer(default = 0)

    # Total number of visits currently in store. An optimization for
    # forgetting/maxCount.
    visitCount = attributes.integer(default = 0)

    # Caching needs to be provisioned/bestowed
    caching = attributes.boolean(default=False)

    # Number of MRU visits to keep
    maxCount = attributes.integer(default=1000)

    installedOn = attributes.reference()
    prefAggregator = attributes.inmemory()
    bookmarkVisit = attributes.inmemory()
    _tzinfo = attributes.inmemory()
    powerupInterfaces = (iclickchronicle.IClickRecorder,)

    def activate(self):
        self._tzinfo = None
        self.bookmarkVisit = self.store.findOrCreate(BookmarkVisit)
        self.prefAggregator = None

    def _getTzinfo(self):
        if self._tzinfo is None:
            prefs = ixmantissa.IPreferenceAggregator(self.store)
            tzname = prefs.getPreferenceValue('timezone')
            self._tzinfo = pytz.timezone(tzname)
        return self._tzinfo

    tzinfo = property(_getTzinfo)

    def createResource(self):
        return URLGrabber(self)

    def getDomain(self, host):
        for domain in self.store.query(Domain, Domain.url==host):
            if domain.ignore:
                return None
            break
        else:
            favIcon = self.store.findUnique(indexinghelp.DefaultFavicon,
                                            default=None)
            if favIcon is None:
                images = FilePath(__file__).parent().child('static').child('images')
                favIcon = indexinghelp.DefaultFavicon(
                                        store=self.store,
                                        data=images.child('favicon.png').getContent())

            domain = Domain(url=host, store=self.store,
                            favIcon=favIcon, timestamp=Time())
        return domain

    def recordBookmark(self, title, url, tags, indexIt=True, storeFavicon=True):
        host = str(URL.fromString(url).click("/"))
        timeNow = Time()

        domain = self.getDomain(host)
        if domain is None:
            return
        domain.timestamp = timeNow

        for bookmark in self.store.query(Bookmark, Bookmark.url == url):
            bookmark.timestamp = timeNow
            break
        else:
            bookmark = Bookmark(store=self.store,
                                title=title,
                                url=url,
                                domain=domain,
                                referrer=self.bookmarkVisit,
                                timestamp=timeNow)
        catalog = None
        for tag in filter(len, tags):
            if catalog is None:
                catalog = self.store.findOrCreate(Catalog)
            catalog.tag(bookmark, unicode(tag.strip()))

        cacheMan = iclickchronicle.ICache(self.store)
        cacheMan.rememberVisit(bookmark,
                               cacheIt=self.caching,
                               indexIt=indexIt,
                               storeFavicon=storeFavicon)

    def recordClick(self, qargs, indexIt=True, storeFavicon=True):
        """
        Extract POST arguments and create a Visit object before indexing and caching.
        """
        # if the recording of this visit is going to push us over the limit
        # then delete the oldest visit
        if self.maxCount < self.visitCount+1:
            self.forgetOldestVisit()

        (url,) = qargs.get('url', (None,))
        if url is None:
            # No url, no deal.
            return
        (title,) = qargs.get('title', (None,))
        if not title or title.isspace():
            title = url

        title = title.decode('utf-8')

        (ref,) = qargs.get('ref', (None,))
        if qargs.get('bookmark', (None,))[0] is not None:
            self.recordBookmark(title, url, qargs.get('tags', ()), indexIt=indexIt, storeFavicon=storeFavicon)
            return

        if ref:
            # we got some value for "ref".  pass the referrer url to
            # findOrCreateVisit, using same for title, because on the
            # off chance that we didn't record the click when the user
            # was viewing the referrer page, we don't have much else
            # meaningful to use
            referrer, created = self.findOrCreateVisit(ref,
                                              unicode(ref),
                                              indexIt=indexIt,
                                              storeFavicon=storeFavicon)
        else:
            # Most likely selected a bookmark/shortcut
            referrer = self.bookmarkVisit

        visit, created = self.findOrCreateVisit(
            url, title,
            referrer, indexIt=indexIt,
            storeFavicon=storeFavicon)

        if (visit is not None
                and created is True
                and not visit.domain.private):

            self.publicize(title, url)
        else:
            self.publicize(u'', ONLY_INCREMENT)

    def publicize(self, title, url):
        if self.prefAggregator is None:
            self.prefAggregator = ixmantissa.IPreferenceAggregator(self.store)

        if not self.prefAggregator.getPreferenceValue("shareClicks"):
            url = ONLY_INCREMENT

        sendToPublicPage(
            self.store,
            q2q.Q2QAddress("clickchronicle.com", "clickchronicle"),
            AGGREGATION_PROTOCOL,
            AggregateClick(title=title, url=url))

    def findOrCreateVisit(self, url, title, referrer=None, indexIt=True, storeFavicon=True):
        """
        Try to find a visit to the same url TODAY.
        If found update the timestamp and return it.
        Otherwise create a new Visit.
        Return a tuple of visit, created
        Visit can be a new visit, an existing visit or None.
        created is True of False depending on whether or not a visit was created.
        """
        host = str(URL.fromString(url).click("/"))
        domain = self.getDomain(host)
        if domain is None:
            return (None, False)
        # Defensive coding. Never allow visit.referrer to be None.
        # May need to be revisited
        if referrer is None:
            referrer = self.bookmarkVisit
        existingVisit = self.findVisitForToday(url)
        timeNow = Time()

        if existingVisit:
            # Already visited today
            # XXX What should we do about referrer for existing visit
            # XXX we'll conveniently ignore it for now
            def _():
                domain.timestamp = timeNow
                existingVisit.timestamp = timeNow
                existingVisit.visitCount += 1
                existingVisit.domain.visitCount += 1
                existingVisit.referrer = referrer
                bookmark = existingVisit.getBookmark()
                if bookmark:
                    bookmark.visitCount += 1
                return existingVisit
            return self.store.transact(_), False

        # New visit today
        def _():
            domain.timestamp = timeNow
            visit = Visit(store = self.store,
                          url = url,
                          timestamp = timeNow,
                          title = title,
                          domain = domain,
                          referrer = referrer)
            bookmark = visit.getBookmark()
            if bookmark:
                bookmark.visitCount += 1
            self.visitCount += 1
            domainList = self.store.findFirst(DomainList)
            domainList.clicks += 1
            self.clickCount += 1
            visit.visitCount += 1
            visit.domain.visitCount +=1
            return visit

        visit = self.store.transact(_)

        cacheMan = iclickchronicle.ICache(self.store)
        cacheMan.rememberVisit(visit,
                               cacheIt=self.caching,
                               indexIt=indexIt,
                               storeFavicon=storeFavicon)
        return visit, True


    def findVisitForToday(self, url):
        timeNow = Time()
        dtNow = timeNow.asDatetime(self.tzinfo)
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

    def forgetVisit(self, visit):
        indexer = iclickchronicle.IIndexer(self.store)
        indexer.delete(visit)
        cacheMan = iclickchronicle.ICache(self.store)
        cacheMan.forget(visit)
        def _():
            for refvisit in self.store.query(Visit, Visit.referrer == visit):
                refvisit.referrer = self.bookmarkVisit
            visit.deleteFromStore()
            self.visitCount -= 1
        self.store.transact(_)

    def bulkForgetVisits(self, visitList):
        indexer = iclickchronicle.IIndexer(self.store)
        indexer.bulkDelete(visitList)
        cacheMan = iclickchronicle.ICache(self.store)
        for visit in visitList:
            cacheMan.forget(visit)
        def _():
            for visit in visitList:
                for refvisit in self.store.query(Visit, Visit.referrer == visit):
                    refvisit.referrer = self.bookmarkVisit
                visit.deleteFromStore()
            self.visitCount -= len(visitList)
        self.store.transact(_)

    def forgetOldestVisit(self):
        """
        Remove oldest Visit from the store, cache and index.
        """
        # XXX - This needs to be more sophisticated since there is a known race
        # condition for a Visit being deleted from the index before the page has
        # been fetched and indexed/cahced
        visit = iter(self.store.query(Visit, sort=Visit.timestamp.ascending)).next()
        self.forgetVisit(visit)

    def ignoreVisit(self, visit):
        def txn():
            if hasattr(visit, 'domain'):
                visit.domain.ignore = True
                comparison = Visit.domain == visit.domain
            else:
                visit.ignore = True
                comparison = Visit.domain == visit
            visitsToDelete = list(self.store.query(Visit, comparison))
            self.bulkForgetVisits(visitsToDelete)
        self.store.transact(txn)

    def deleteDomain(self, domain):
        # Oh so close to ignoreVisit
        def txn():
            visitsToDelete = list(self.store.query(Visit, Visit.domain == domain))
            visitsToDelete.extend(self.store.query(Bookmark, Bookmark.domain == domain))
            self.bulkForgetVisits(visitsToDelete)
            domain.deleteFromStore()
        self.store.transact(txn)


def staticShellContent1To2(oldShell):
    newShell = oldShell.upgradeVersion(
        'clickchronicle_static_shell_content', 1, 2,
        installedOn=oldShell.store)
    return newShell
upgrade.registerUpgrader(staticShellContent1To2, 'clickchronicle_static_shell_content', 1, 2)



class URLGrabber(rend.Page):
    """I handle Bookmarker/ClickRecorder's HTTP action.  i am not an Item
       because i have a lot of attributes inherited from rend.Page"""
    def __init__(self, recorder):
        self.recorder = recorder

    def renderHTTP(self, ctx):
        """get url and title GET variables, supplying sane defaults"""
        urlpath = inevow.IRequest(ctx).URLPath()
        qargs = dict()
        for (k, v) in urlpath.queryList():
            qargs.setdefault(k, list()).append(v)

        self.recorder.recordClick(qargs)
        request = inevow.IRequest(ctx)
        referrer = request.getHeader('referer')

        if referrer:
            return redirectTo(referrer, request)
        return ''

import pytz
from datetime import datetime, timedelta
from zope.interface import implements

from twisted.cred import portal
from twisted.python.components import registerAdapter

from nevow.url import URL
from nevow import rend, inevow, tags, flat, livepage, entities

from epsilon.extime import Time

from axiom.item import Item, InstallableMixin
from axiom import upgrade, userbase, scheduler, attributes

from vertex import q2q

from xmantissa import ixmantissa, webnav, website, webapp, prefs, search
from xmantissa.publicresource import PublicPage

from clickchronicle import iclickchronicle
from clickchronicle import indexinghelp
from clickchronicle.util import PagedTableMixin, SortablePagedTableMixin
from clickchronicle.util import staticTemplate, makeScriptTag
from clickchronicle.visit import Visit, Domain, BookmarkVisit, Bookmark
from clickchronicle.searchparser import parseSearchString
from clickchronicle.publicpage import AGGREGATION_PROTOCOL, AggregateClick, CCPublicPageMixin

from xapwrap.index import NoIndexValueFound

flat.registerFlattener(lambda t, ign: t.asHumanly(), Time)

class CCPrivatePagedTableMixin(website.AxiomFragment):
    maxTitleLength = 60
    defaultFavIconPath = "/static/images/favicon.png"

    def __init__(self, original, docFactory=None):
        self.store = original.store
        website.AxiomFragment.__init__(self, original, docFactory)

        self.translator = ixmantissa.IWebTranslator(original.installedOn)
        self.clickList = original.store.query(ClickList).next()
        self.pagingPatterns = inevow.IQ(self.translator.getDocFactory("paging-patterns"))
        prefAggregator = ixmantissa.IPreferenceAggregator(original.installedOn)
        self.itemsPerPage = prefAggregator.getPreferenceValue('itemsPerPage')
        self.patterns = dict()

        pgen = self.pagingPatterns.patternGenerator
        for pname in ("clickTable", "pagingWidget", "navBar", "visitInfo", "clickActions",
                      "visitRow", "bookmarkedVisitRow", "bookmarkActions", "clickInfoRow"):
            self.patterns[pname] = pgen(pname)

    def head(self):
        yield makeScriptTag("/static/js/fadomatic.js")
        yield makeScriptTag("/static/js/MochiKit/MochiKit.js")
        yield makeScriptTag("/static/js/paged-table.js")

    def handle_block(self, ctx, visitStoreID):
        store = self.original.store
        visit = store.getItemByID(int(visitStoreID))
        iclickchronicle.IClickRecorder(store).ignoreVisit(visit)
        # rewind to the first page, to reflect changes
        # it's a toss-up whether it's best to rewind of stay on the current page
        yield (livepage.js.blocked(self.trimTitle(visit.url)), livepage.eol)
        yield self.handle_updateTable(ctx, self.startPage)

    def handle_bookmark(self, ctx, visitStoreID):
        store = self.original.store
        visit = store.getItemByID(int(visitStoreID))
        def _():
            bookmark=visit.asBookmark()
            return bookmark
        bm = self.store.transact(_)

        yield (livepage.js.bookmarked(self.trimTitle(visit.url)), livepage.eol)
        yield self.handle_updateTable(ctx, self.currentPage)

    def handle_delete(self, ctx, visitStoreID):
        store = self.original.store
        visit = store.getItemByID(int(visitStoreID))
        clickApp = iclickchronicle.IClickRecorder(store)
        def _():
            clickApp.forgetVisit(visit)
        self.store.transact(_)

        yield (livepage.js.deleted(self.trimTitle(visit.url)), livepage.eol)
        yield self.handle_updateTable(ctx, self.currentPage)

    def visitInfo(self, visit):
        newest = visit.getLatest(count=1).next()

        return (("URL", tags.a(href=visit.url)[self.trimTitle(visit.url)]),
                ("Referrer", visit.referrer.title),
                ("Last Visited", newest.timestamp))

    def handle_info(self, ctx, visitStoreID):
        store = self.original.store
        visit = store.getItemByID(int(visitStoreID))
        visit = iclickchronicle.IDisplayableVisit(visit)

        data = self.visitInfo(visit)
        return (livepage.js.gotInfo(visitStoreID, self.patterns["visitInfo"](data=data)), livepage.eol)

    def trimTitle(self, title):
        if self.maxTitleLength < len(title):
            title = "%s..." % title[:self.maxTitleLength - 3]
        return title

    def prepareVisited(self, visited):
        visited = iclickchronicle.IDisplayableVisit(visited)
        (desc, icon) = (visited.asDict(), visited.asIcon())

        if icon is None:
            iconPath = self.defaultFavIconPath
        else:
            iconPath = '/' + icon.prefixURL

        desc.update(icon=iconPath, title=self.trimTitle(desc["title"]))
        return desc

    def constructTable(self, ctx, rows):
        content = []
        for row in rows:
            if row["bookmarked"]:
                rowPattern = "bookmarkedVisitRow"
                actionsPattern = "bookmarkActions"
            else:
                rowPattern = "visitRow"
                actionsPattern = "clickActions"

            p = self.patterns[rowPattern](data=row)
            p = p.fillSlots("clickActions", self.patterns[actionsPattern]())
            content.extend((p, self.patterns["clickInfoRow"]()))

        return self.patterns["clickTable"].fillSlots("rows", content)

class CCPrivatePagedTable(CCPrivatePagedTableMixin, PagedTableMixin):
    pass

class CCPrivateSortablePagedTable(CCPrivatePagedTableMixin, SortablePagedTableMixin):
    pagingItem = None

    def __init__(self, original, docFactory=None):
        CCPrivatePagedTableMixin.__init__(self, original, docFactory)
        self.patterns["clickTable"] = self.pagingPatterns.patternGenerator("sortableClickTable")

    def generateRowDicts(self, ctx, pageNumber, sortCol, sortDirection):
        sort = getattr(getattr(self.pagingItem, sortCol), sortDirection)
        store = self.original.store
        offset = (pageNumber - 1) * self.itemsPerPage

        for v in store.query(self.pagingItem, sort = sort,
                             limit = self.itemsPerPage, offset = offset):

            yield self.prepareVisited(v)

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

    def endow(self, ticket, avatar):
        self.endowed += 1

        avatar.findOrCreate(website.WebSite).installOn(avatar)
        avatar.findOrCreate(webapp.PrivateApplication,
                            preferredTheme=u'cc-skin').installOn(avatar)
        avatar.findOrCreate(scheduler.SubScheduler).installOn(avatar)
        avatar.findOrCreate(ClickChronicleInitializer,
                            maxClicks=self.maxClicks).installOn(avatar)
        avatar.findOrCreate(StaticShellContent).installOn(avatar)

def benefactor1To2(oldBene):
    newBene = oldBene.upgradeVersion(
        'clickchronicle_benefactor', 1, 2,
        endowed=oldBene.endowed,
        maxClicks=1000)
    return newBene
upgrade.registerUpgrader(benefactor1To2, 'clickchronicle_benefactor', 1, 2)


class _ShareClicks(prefs.MultipleChoicePreference):
    def __init__(self, value, collection):
        valueToDisplay = {True:"Yes", False:"No"}
        desc = 'If set to "Yes", your clicks will be aggregated anonymously'
        super(_ShareClicks, self).__init__('shareClicks', value,
                                           'Share Clicks (Anonymously)',
                                           collection, desc,
                                           valueToDisplay)

class _TimezonePreference(prefs.Preference):
    def __init__(self, value, collection):
        super(_TimezonePreference, self).__init__('timezone', value, 'Timezone',
                                                  collection, 'Your current timezone')

    def choices(self):
        return pytz.common_timezones

    def displayToValue(self, display):
        return unicode(display)

    def valueToDisplay(self, value):
        return str(value)

class CCPreferenceCollection(Item):
    implements(ixmantissa.IPreferenceCollection)

    schemaVersion = 1
    typeName = 'clickchronicle_preference_collection'
    name = 'ClickChronicle Preferences'

    installedOn = attributes.reference()
    shareClicks = attributes.boolean(default=True)
    timezone = attributes.text(default=u'US/Eastern')
    _cachedPrefs = attributes.inmemory()

    def installOn(self, other):
        assert self.installedOn is None, 'cannot install CCPreferenceCollection on more than one thing!'
        other.powerUp(self, ixmantissa.IPreferenceCollection)
        self.installedOn = other

    def activate(self):
        self._cachedPrefs = {"shareClicks" : _ShareClicks(self.shareClicks, self),
                             "timezone" : _TimezonePreference(self.timezone, self)}

    def getPreferences(self):
        return self._cachedPrefs

    def setPreferenceValue(self, pref, value):
        # see comment in xmantissa.prefs.DefaultPreferenceCollection
        assert hasattr(self, pref.key)
        setattr(pref, 'value', value)
        self.store.transact(lambda: setattr(self, pref.key, value))

class ClickChronicleInitializer(Item):
    """
    Installed by the Click Chronicle benefactor, this Item presents
    itself as a page for initializing your password.  Once done, the
    actual ClickChronicle powerups are installed.
    """
    implements(ixmantissa.INavigableElement)

    typeName = 'clickchronicle_password_initializer'
    schemaVersion = 2

    installedOn = attributes.reference()
    maxClicks = attributes.integer()

    def installOn(self, other):
        assert self.installedOn is None, "Cannot install ClickChronicleInitializer on more than one thing"
        other.powerUp(self, ixmantissa.INavigableElement)
        self.installedOn = other

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

    def _reallyEndow(self):
        avatar = self.installedOn

        rec = avatar.findOrCreate(ClickRecorder)
        rec.maxCount = self.maxClicks
        rec.installOn(avatar)

        for item in (ClickList, DomainList, indexinghelp.SyncIndexer,
                     BookmarkList, CCSearchProvider, indexinghelp.CacheManager,
                     GetExtension, CCPreferenceCollection):
            avatar.findOrCreate(item).installOn(avatar)

        avatar.powerDown(self, ixmantissa.INavigableElement)
        self.deleteFromStore()

def initializer1To2(oldInit):
    newInit = oldInit.upgradeVersion(
        'clickchronicle_password_initializer', 1, 2,
        installedOn=oldInit.installedOn,
        maxClicks=oldInit.maxClicks)
    return newInit
upgrade.registerUpgrader(initializer1To2, 'clickchronicle_password_initializer', 1, 2)


class ClickChronicleInitializerPage(CCPublicPageMixin, PublicPage):

    def __init__(self, original):
        PublicPage.__init__(self, original, staticTemplate("initialize.html"),
                            ixmantissa.IStaticShellContent(original.installedOn, None),
                            original.installedOn)

    def render_head(self, ctx, data):
        yield CCPublicPageMixin.render_head(self, ctx, data)
        yield makeScriptTag("/static/js/initialize.js")

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
        """show a link to myself in the navbar"""
        return [webnav.Tab('Clicks', self.storeID, 0.2)]

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
        return [webnav.Tab('Domains', self.storeID, 0.1)]

class ClickListFragment(CCPrivateSortablePagedTable):
    '''i adapt ClickList to INavigableFragment'''
    implements(ixmantissa.INavigableFragment)
    title = 'Click List'

    fragmentName = 'click-list-fragment'
    live = True

    pagingItem = Visit
    sortDirection = 'descending'
    sortColumn = 'timestamp'

    def render_maxCount(self, ctx, data):
        return ctx.tag[iclickchronicle.IClickRecorder(self.original.store).maxCount]

    def countTotalItems(self, ctx):
        return iclickchronicle.IClickRecorder(self.original.store).visitCount

registerAdapter(ClickListFragment,
                ClickList,
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

    def installOn(self, other):
        assert self.installedOn is None, "Cannot install BookmarkList on more than one thing"
        other.powerUp(self, ixmantissa.INavigableElement)
        self.installedOn = other

    def getTabs(self):
        '''show a link to myself in the navbar'''
        return [webnav.Tab('Bookmarks', self.storeID, 0.1)]

class BookmarkListFragment(CCPrivateSortablePagedTable):
    '''i adapt BookmarkList to INavigableFragment'''
    implements(ixmantissa.INavigableFragment)

    fragmentName = 'bookmark-list-fragment'
    live = True
    title = 'Bookmark List'

    pagingItem = Bookmark
    sortDirection = 'descending'
    sortColumn = 'timestamp'

    def __init__(self, original, docFactory=None):
        CCPrivateSortablePagedTable.__init__(self, original, docFactory)
        self.patterns["visitRow"] = self.patterns["bookmarkedVisitRow"]

    def countTotalItems(self, ctx):
        return self.original.installedOn.count(self.pagingItem)

    def visitInfo(self, bm):
        return (("URL", tags.a(href=bm.url)[self.trimTitle(bm.url)]),
                ("Referrer", bm.referrer.title),
                ("Created", bm.timestamp))

registerAdapter(BookmarkListFragment,
                BookmarkList,
                ixmantissa.INavigableFragment)

class DomainListFragment(CCPrivateSortablePagedTable):
    '''i adapt DomainList to INavigableFragment'''
    implements(ixmantissa.INavigableFragment)

    fragmentName = 'domain-list-fragment'
    live = True
    title = 'Domain List'

    pagingItem = Domain
    sortDirection = 'descending'
    sortColumn = 'timestamp'

    def handle_delete(self, ctx, visitStoreID):
        store = self.original.store
        domain = store.getItemByID(int(visitStoreID))
        clickApp = iclickchronicle.IClickRecorder(store)
        def _():
            clickApp.deleteDomain(domain)
        self.store.transact(_)
        yield (livepage.js.deleted(domain.url), livepage.eol)
        yield self.handle_updateTable(ctx, self.currentPage)

    def handle_block(self, ctx, visitStoreID):
        store = self.original.store
        domain = store.getItemByID(int(visitStoreID))
        clickApp = iclickchronicle.IClickRecorder(store)
        visit = store.findFirst(Visit, domain=domain)
        def _():
            if visit:
                iclickchronicle.IClickRecorder(store).ignoreVisit(visit)
            else:
                domain.ignore = True
        store.transact(_)
        yield (livepage.js.blocked(self.trimTitle(domain.url)), livepage.eol)
        yield self.handle_updateTable(ctx, self.currentPage)

    def visitInfo(self, visit):
        newest = visit.getLatest(count=1).next()

        return (("URL", tags.a(href=visit.url)[self.trimTitle(visit.url)]),
                ("Last Visited", newest.timestamp))

    def countTotalItems(self, ctx):
        return self.original.installedOn.count(self.pagingItem)

registerAdapter(DomainListFragment,
                DomainList,
                ixmantissa.INavigableFragment)

class GetExtension(Item):
    implements(ixmantissa.INavigableElement)
    typeName = 'clickchronicle_get_extension'
    schemaVersion = 1

    installedOn = attributes.reference()

    def installOn(self, other):
        assert self.installedOn is None, "cannot install GetExtension on more than one thing!"
        other.powerUp(self, ixmantissa.INavigableElement)
        self.installedOn = other

    def getTabs(self):
        return [webnav.Tab('Get Extension', self.storeID, 0.0)]

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
    recip = realm.accountByAddress(u"clickchronicle", u"clickchronicle.com")
    if recip is not None:
        ixmantissa.IPublicPage(recip).observeClick(message.structured['title'], message.structured['url'])


class ChangeClickLimit(Item):
    typeName = 'clickchronicle_click_changer'
    schemaVersion = 1

    byWhat = attributes.integer()
    recorder = attributes.reference()

    def schedule(self, howLong):
        """
        Set this Item's run method to be run in C{howLong} seconds
        from now.
        """
        scheduler.IScheduler(self.store).schedule(
            self,
            Time() + timedelta(seconds=howLong))

    def run(self):
        self.recorder.maxCount += self.byWhat
        self.deleteFromStore()

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
    caching = attributes.boolean(default=True)
    # Number of MRU visits to keep
    maxCount = attributes.integer(default=1000)
    bookmarkVisit = attributes.inmemory()
    installedOn = attributes.reference()
    prefAggregator = attributes.inmemory()

    def installOn(self, other):
        assert self.installedOn is None, "Cannot install ClickRecorder on more than one thing"
        super(ClickRecorder, self).installOn(other)
        other.powerUp(self, iclickchronicle.IClickRecorder)
        self.installedOn = other

    def activate(self):
        self.bookmarkVisit = self.store.findOrCreate(BookmarkVisit)
        self.prefAggregator = None

    def createResource(self):
        return URLGrabber(self)

    def raiseClickLimitForDuration(self, byWhat, howLong):
        ChangeClickLimit(store=self.store, recorder=self, byWhat=-byWhat).schedule(howLong)
        self.maxCount += byWhat

    def recordClick(self, qargs, indexIt=True, storeFavicon=True):
        """
        Extract POST arguments and create a Visit object before indexing and caching.
        """
        # if the recording of this visit is going to push us over the limit
        # then delete the oldest visit
        if self.maxCount < self.visitCount+1:
            self.forgetOldestVisit()

        url = qargs.get('url')
        if url is None:
            # No url, no deal.
            return
        title = qargs.get('title')
        if not title or title.isspace():
            title = url

        title = title.decode('utf-8')

        ref = qargs.get('ref')

        if ref:
            # we got some value for "ref".  pass the referrer url to
            # findOrCreateVisit, using same for title, because on the
            # off chance that we didn't record the click when the user
            # was viewing the referrer page, we don't have much else
            # meaningful to use
            referrer = self.findOrCreateVisit(ref,
                                              unicode(ref),
                                              indexIt=indexIt,
                                              storeFavicon=storeFavicon)
        else:
            # Most likely selected a bookmark/shortcut
            referrer = self.bookmarkVisit

        visit = self.findOrCreateVisit(
            url, title,
            referrer, indexIt=indexIt,
            storeFavicon=storeFavicon)

        if visit is not None:
            # Ignored domain
            if self.prefAggregator is None:
                self.prefAggregator = ixmantissa.IPreferenceAggregator(self.installedOn)

            if self.prefAggregator.getPreferenceValue("shareClicks"):
                sendToPublicPage(
                    self.installedOn,
                    q2q.Q2QAddress("clickchronicle.com", "clickchronicle"),
                    AGGREGATION_PROTOCOL,
                    AggregateClick(title=title, url=url))

    def findOrCreateVisit(self, url, title, referrer=None, indexIt=True, storeFavicon=True):
        """
        Try to find a visit to the same url TODAY.
        If found update the timestamp and return it.
        Otherwise create a new Visit.
        """
        host = str(URL.fromString(url).click("/"))
        domain = self.store.findOrCreate(Domain, url=host)
        if domain.ignore:
            return None
        # Defensive coding. Never allow visit.referrer to be None.
        # May need to be revisited
        if referrer is None:
            referrer = self.bookmarkVisit
        existingVisit = self.findVisitForToday(url)
        timeNow = Time.fromDatetime(datetime.now())

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
                return existingVisit
            return self.store.transact(_)

        # New visit today
        def _():
            domain.timestamp = timeNow
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

        cacheMan = iclickchronicle.ICache(self.store)
        cacheMan.rememberVisit(visit,
                               cacheIt=self.caching,
                               indexIt=indexIt,
                               storeFavicon=storeFavicon)
        return visit


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

    def forgetVisit(self, visit):
        indexer = iclickchronicle.IIndexer(self.store)
        indexer.delete(visit)
        cacheMan = iclickchronicle.ICache(self.store)
        cacheMan.forget(visit)
        def _():
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
        visit = self.store.query(Visit, sort=Visit.timestamp.ascending).next()
        self.forgetVisit(visit)

    def ignoreVisit(self, visit):
        def txn():
            # ignore the Domain
            visit.domain.ignore = True
            visitsToDelete = list(self.store.query(Visit, Visit.domain == visit.domain))
            self.bulkForgetVisits(visitsToDelete)
        self.store.transact(txn)

    def deleteDomain(self, domain):
        # Oh so close to ignoreVisit
        def txn():
            visitsToDelete = list(self.store.query(Visit, Visit.domain == domain))
            self.bulkForgetVisits(visitsToDelete)
            domain.deleteFromStore()
        self.store.transact(txn)

class StaticShellContent(Item, InstallableMixin):
    implements(ixmantissa.IStaticShellContent)

    schemaVersion = 2
    typeName = 'clickchronicle_static_shell_content'

    installedOn = attributes.reference()

    def installOn(self, other):
        super(StaticShellContent, self).installOn(other)
        other.powerUp(self, ixmantissa.IStaticShellContent)

    def getHeader(self):
        return tags.a(href="/")[tags.img(border=0, src="/static/images/logo.png")]

    def getFooter(self):
        return (entities.copy, "Divmod 2005")

def staticShellContent1To2(oldShell):
    newShell = oldShell.upgradeVersion(
        'clickchronicle_static_shell_content', 1, 2,
        installedOn=oldShell.store)
    return newShell
upgrade.registerUpgrader(staticShellContent1To2, 'clickchronicle_static_shell_content', 1, 2)


class CCSearchProvider(Item):
    implements(ixmantissa.ISearchProvider)
    installedOn = attributes.reference()
    schemaVersion = 1
    typeName = 'clickchronicle_search_provider'

    indexer = attributes.inmemory()

    def installOn(self, other):
        assert self.installedOn is None, "cannot install SearchProvider on more than one thing"
        other.powerUp(self, ixmantissa.ISearchProvider)
        self.installedOn = other

    def activate(self):
        self.indexer = None

    def _cachePowerups(self):
        self.indexer = iclickchronicle.IIndexer(self.installedOn)

    def count(self, term):
        if self.indexer is None:
            self._cachePowerups()

        term = ' '.join(parseSearchString(term))
        (estimated, total) = self.indexer.count(term)
        return estimated

    def search(self, term, count, offset):
        if self.indexer is None:
            self._cachePowerups()

        term = ' '.join(parseSearchString(term))

        doSearch = lambda **k: self.indexer.search(term, startingIndex=offset,
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
            yield search.SearchResult(description=visit.title, url=visit.url,
                                      summary=spec.get('values', dict()).get('summary', ''),
                                      timestamp=visit.timestamp,
                                      score=spec['score'] / 100.0)

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

import collections
from datetime import datetime, timedelta
from zope.interface import implements

from twisted.cred import portal
from twisted.python import util, log
from twisted.python.components import registerAdapter

from nevow.url import URL
from nevow import rend, inevow, tags, loaders, flat, livepage, entities

from epsilon.extime import Time

from axiom.item import Item
from axiom import userbase, scheduler, attributes

from vertex import juice, q2q

from xmantissa import ixmantissa, webnav, website, webapp
from xmantissa.webgestalt import AuthenticationApplication
from xmantissa.publicresource import PublicLivePage, PublicPage

from clickchronicle import iclickchronicle
from clickchronicle import indexinghelp
from clickchronicle.util import (PagedTableMixin,
                                 SortablePagedTableMixin)
from clickchronicle.visit import Visit, Domain, BookmarkVisit, Bookmark
from clickchronicle.searchparser import parseSearchString

flat.registerFlattener(lambda t, ign: t.asHumanly(), Time)

AGGREGATION_PROTOCOL = 'clickchronicle-click-aggregation-protocol'

class AggregateClick(juice.Command):
    commandName = 'Aggregate-Click'

    arguments = [('title', juice.Unicode()),
                 ('url', juice.String())]

class ClickChroniclePublicPage(Item):
    implements(ixmantissa.IPublicPage, inevow.IResource)

    typeName = 'clickchronicle_public_page'
    schemaVersion = 1

    installedOn = attributes.reference()

    clickListeners = attributes.inmemory()
    recentClicks = attributes.inmemory()

    def activate(self):
        self.clickListeners = []
        self.recentClicks = collections.deque()

    def installOn(self, other):
        assert self.installedOn is None, "Cannot install ClickChroniclePublicPage on more than one thing"
        other.powerUp(self, ixmantissa.IPublicPage)
        self.installedOn = other

    def createResource(self):
        return PublicIndexPage(self)

    def observeClick(self, title, url):
        self.recentClicks.append((title, url))
        if len(self.recentClicks) > 10:
            self.recentClicks.popleft()

        # XXX Desync this, it's gonna get slow.
        for listener in self.clickListeners:
            listener.observeClick(title, url)

    def listenClicks(self, who):
        self.clickListeners.append(who)
        return lambda: self.clickListeners.remove(who)


staticTemplate = lambda fname: loaders.xmlfile(util.sibpath(__file__, "static/html/" + fname))

class CCPublicPageMixin(object):
    headerFragment = staticTemplate("header.html")
    navigationFragment = staticTemplate("static-nav.html")
    title = "ClickChronicle"
    footer = flat.flatten((entities.copy, "Divmod 2005"))

    def render_head(self, ctx, data):
        yield super(CCPublicPageMixin, self).render_head(ctx, data)
        yield tags.title[self.title]
        yield tags.link(rel="stylesheet", type="text/css", href="/static/css/static-site.css")

    def render_topPanel(self, ctx, data):
        return ctx.tag[self.headerFragment]

    def render_navigation(self, ctx, data):
        return ctx.tag[self.navigationFragment]

    def render_footer(self, ctx, data):
        return ctx.tag[self.footer]

class CCPublicPage(CCPublicPageMixin, PublicPage):
    def __init__(self, original, fragment):
        PublicPage.__init__(self, original, fragment)
        self.docFactory = staticTemplate("static-shell.html")

class PublicIndexPage(CCPublicPageMixin, PublicLivePage):
    def __init__(self, original):
        PublicLivePage.__init__(self, original, staticTemplate("index.html"))
        self.docFactory = staticTemplate("static-shell.html")
        mkchild = lambda tmplname: CCPublicPage(original, staticTemplate(tmplname))
        self.children =  {"privacy-policy" : mkchild("privacy-policy.html"),
                          "faq" : mkchild("faq.html")}

    def render_head(self, ctx, data):
        yield CCPublicPageMixin.render_head(self, ctx, data)
        yield makeScriptTag("/static/js/live-clicks.js")

    def goingLive(self, ctx, client):
        self.client = client
        unlisten = self.original.listenClicks(self)
        client.notifyOnClose().addCallback(lambda ign: unlisten())
        client.send([
            (livepage.js.clickchronicle_addClick(t, u), livepage.eol)
            for (t, u) in self.original.recentClicks])

    def child_(self, ctx):
        return self

    def observeClick(self, title, url):
        self.client.send(livepage.js.clickchronicle_addClick(title, url))


def makeScriptTag(src):
    return tags.script(type="application/x-javascript", src=src)

class TopPanel(Item):
    implements(ixmantissa.INavigableElement)
    typeName = 'clickchronicle_toppanel'
    schemaVersion = 1

    searches = attributes.integer(default=0)
    installedOn = attributes.reference()

    def installOn(self, other):
        assert self.installedOn is None, "Cannot install TopPanel on more than one thing"
        other.powerUp(self, ixmantissa.INavigableElement)
        self.installedOn = other

    def topPanelContent(self):
        translator = ixmantissa.IWebTranslator(self.installedOn, None)
        docFactory = inevow.IQ(translator.getDocFactory("top-panel-fragment"))
        topPanelPattern = docFactory.patternGenerator("top-panel")
        (username, domain), = userbase.getAccountNames(self.installedOn)
        return [
            tags.a(href='/static/clickchronicle.xpi')['Get the Extension!'],
            topPanelPattern.fillSlots(
                "form-action", translator.linkTo(self.storeID)
            ).fillSlots("username", '%s@%s' % (username, domain))]

    def getTabs(self):
        return []

class CCPrivatePagedTableMixin(website.AxiomFragment):
    maxTitleLength = 60
    defaultFavIconPath = "/static/images/favicon.png"

    def __init__(self, original, docFactory=None):
        self.store = original.store
        website.AxiomFragment.__init__(self, original, docFactory)

        self.translator = ixmantissa.IWebTranslator(original.installedOn)
        self.clickList = original.store.query(ClickList).next()
        self.itemsPerPage = original.store.query(Preferences).next().itemsPerPage
        self.pagingPatterns = inevow.IQ(self.translator.getDocFactory("paging-patterns"))
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
    schemaVersion = 1

    endowed = attributes.integer(default = 0)

    def endow(self, ticket, avatar):
        self.endowed += 1

        avatar.findOrCreate(website.WebSite).installOn(avatar)
        avatar.findOrCreate(webapp.PrivateApplication,
                            preferredTheme=u'cc-skin').installOn(avatar)
        avatar.findOrCreate(scheduler.SubScheduler).installOn(avatar)
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
                     ClickRecorder, indexinghelp.SyncIndexer, BookmarkList,
                     TopPanel, AuthenticationApplication, indexinghelp.CacheManager):
            avatar.findOrCreate(item).installOn(avatar)

        avatar.powerDown(self, ixmantissa.INavigableElement)
        self.deleteFromStore()


class ClickChronicleInitializerPage(CCPublicPageMixin, PublicPage):

    def __init__(self, original):
        PublicPage.__init__(self, original, staticTemplate("initialize.html"))
        self.docFactory = staticTemplate("static-shell.html")

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
        return [webnav.Tab('Domains', self.storeID, 0.1)]

    def topPanelContent(self):
        return None

class ClickListFragment(CCPrivateSortablePagedTable):
    '''i adapt ClickList to INavigableFragment'''
    implements(ixmantissa.INavigableFragment)

    fragmentName = 'click-list-fragment'
    title = ''
    live = True

    pagingItem = Visit
    sortDirection = 'descending'
    sortColumn = 'timestamp'

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

    def topPanelContent(self):
        return None

class BookmarkListFragment(CCPrivateSortablePagedTable):
    '''i adapt BookmarkList to INavigableFragment'''
    implements(ixmantissa.INavigableFragment)

    fragmentName = 'bookmark-list-fragment'
    title = ''
    live = True

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
    title = ''
    live = True

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

class Preferences(Item):
    """I represent storeable, per-user preference information.
       I implement INavigableElement, so PrivateApplication will
       look for me in the user's store"""
    implements(ixmantissa.INavigableElement)
    typeName = 'clickchronicle_preferences'
    schemaVersion = 1

    installedOn = attributes.reference()
    displayName = attributes.bytes(default='none set')
    homepage = attributes.bytes(default='http://www.clickchronicle.com')
    itemsPerPage = attributes.integer(default=20)

    def installOn(self, other):
        assert self.installedOn is None, "cannot install Preferences on more than one thing!"
        other.powerUp(self, ixmantissa.INavigableElement)
        self.installedOn = other

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
    changePasswordLink = None
    itemsPerPageChoices = (10, 20, 50)

    def head(self):
        yield makeScriptTag("/static/js/MochiKit/MochiKit.js")
        yield makeScriptTag("/static/js/editable-form.js")

    def data_changePasswordLink(self, ctx, data):
        # XXX this is crap, i can't think of an nice way to modify
        # AuthenticationApplication's getTabs(), so we hide subtabs
        # in the navigation template (b/c we use horizontal navigation)
        # and then link to AuthenticationApplication from the prefs template
        if self.changePasswordLink is None:
            avatar = self.original.installedOn
            authApp = avatar.query(AuthenticationApplication).next()
            translator = ixmantissa.IWebTranslator(avatar)
            self.changePasswordLink = translator.linkTo(authApp.storeID)
        return self.changePasswordLink

    def data_preferences(self, ctx, data):
        """
        return a dict of my Preferences instance's columns,
        as well as information about acceptable alternate values
        """
        return dict(displayName = self.original.displayName,
                    homepage = self.original.homepage,
                    itemsPerPage = self.original.itemsPerPage,
                    itemsPerPageChoices = self.itemsPerPageChoices)

registerAdapter(PreferencesFragment,
                Preferences,
                ixmantissa.INavigableFragment)

def send(senderAvatar, toAddress, protocol, message):
    # Haha it is a message passing system
    assert toAddress.resource == "clickchronicle"
    assert toAddress.domain == "clickchronicle.com"
    assert protocol == AGGREGATION_PROTOCOL
    assert isinstance(message, AggregateClick)

    realm = portal.IRealm(senderAvatar.store.parent)
    recip = realm.accountByAddress(u"clickchronicle", u"clickchronicle.com")
    if recip is not None:
        ixmantissa.IPublicPage(recip).observeClick(message.structured['title'], message.structured['url'])


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

    def installOn(self, other):
        assert self.installedOn is None, "Cannot install ClickRecorder on more than one thing"
        super(ClickRecorder, self).installOn(other)
        other.powerUp(self, iclickchronicle.IClickRecorder)
        self.installedOn = other

    def activate(self):
        self.bookmarkVisit = self.store.findOrCreate(BookmarkVisit)

    def createResource(self):
        return URLGrabber(self)

    def recordClick(self, qargs, indexIt=True, storeFavicon=True):
        """
        Extract POST arguments and create a Visit object before indexing and caching.
        """
        if self.visitCount > self.maxCount:
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

        self.findOrCreateVisit(
            url, title,
            referrer, indexIt=indexIt,
            storeFavicon=storeFavicon)

        send(
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
            return
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
        yield makeScriptTag('/static/js/search.js')
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

    def generateRowDicts(self, ctx, pageNumber):
        if self.discriminator is None:
            self.setSearchState(ctx)
        offset = (pageNumber - 1) * self.itemsPerPage
        specs = self.indexer.search(self.discriminator,
                                    startingIndex = offset,
                                    batchSize = self.itemsPerPage)
        store = self.original.store
        for spec in specs:
            visit = store.getItemByID(spec['uid'])
            yield self.prepareVisited(visit)

    def incrementSearches(self):
        def txn():
            self.searchbox.searches += 1
        self.original.store.transact(txn)

registerAdapter(SearchClicks,
                TopPanel,
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

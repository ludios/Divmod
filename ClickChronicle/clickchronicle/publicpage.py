import collections
from xmantissa.publicresource import PublicLivePage, PublicPage
from nevow import inevow, tags, livepage
from clickchronicle.util import makeScriptTag, staticTemplate
from axiom.item import Item
from axiom import attributes
from zope.interface import implements
from xmantissa import ixmantissa
from vertex import juice


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
        return PublicIndexPage(self, ixmantissa.IStaticShellContent(self.installedOn, None))

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


class CCPublicPageMixin(object):
    navigationFragment = staticTemplate("static-nav.html")
    title = "ClickChronicle"

    def render_head(self, ctx, data):
        yield super(CCPublicPageMixin, self).render_head(ctx, data)
        yield tags.title[self.title]
        yield tags.link(rel="stylesheet", type="text/css", href="/static/css/static-site.css")

    def render_navigation(self, ctx, data):
        return ctx.tag[self.navigationFragment]

class CCPublicPage(CCPublicPageMixin, PublicPage):
    pass

class PublicIndexPage(CCPublicPageMixin, PublicLivePage):
    title = 'ClickChronicle'

    def __init__(self, original, staticContent):
        super(PublicIndexPage, self).__init__(original, staticTemplate("index.html"), staticContent)

        def mkchild(tmplname, title):
            p = CCPublicPage(original, staticTemplate(tmplname), staticContent)
            p.title = title
            return p

        self.children =  {"privacy-policy" : mkchild('privacy-policy.html',
                                                     'ClickChronicle Privacy Policy'),
                          "faq" : mkchild('faq.html', 'Clickchronicle FAQ')}

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

# -*- test-case-name: clickchronicle.test.test_publicpage -*-

from __future__ import division

import time, struct, collections
from epsilon import extime
from xmantissa.publicresource import PublicLivePage, PublicPage, GenericPublicPage
from nevow import inevow, tags, livepage
from clickchronicle.util import makeScriptTag, staticTemplate
from clickchronicle.urltagger import tagURL
from axiom.item import Item
from axiom import attributes
from axiom.tags import Catalog, Tag
from zope.interface import implements
from xmantissa import ixmantissa
from vertex import juice

AGGREGATION_PROTOCOL = 'clickchronicle-click-aggregation-protocol'
STATS_INTERVAL = 60 * 60 * 3 # seconds

def _loadHistory(bytes):
    # Note: this is not necessarily good.
    if bytes is None:
        return []
    fmt = '!' + ('I' * (len(bytes) // 4))
    return list(struct.unpack(fmt, bytes))

def _saveHistory(clicks):
    fmt = '!' + ('I' * len(clicks))
    return struct.pack(fmt, *clicks)

class ClickStats(Item):
    """
    This class represents a shallow history or the rate of clicks for
    a particular URL. The actual history is represented as a list of
    integers. The amount of history that is kept is by determined by
    depth, which defines how many data points are stored and interval
    which represents how frequently a data point is added to the
    history. The basic mechanism is that as clicks come in they are
    accumulated by intervalClicks. When the interval (measured in
    seconds) has passed, the value of intervalClicks is appended to
    history and if needed the oldest value of history is popped. All
    operations happen as clicks arrive so as to amortize the cost of
    keeping and updating stats over the interval, rather than doing it
    all at once as the interval expires.

    @ivar depth: how many data points are kept from the past

    @ivar interval: how often a new data point is added to the history

    @ivar intervalClicks: how may clicks have happened since the last
    data point was saved to the history

    @ivar totalClicks: the total number of clicks ever received for
    this URL
    """

    typeName = "click_stats"
    schemaVersion = 1

    score = attributes.integer(default=0) # stores a real. multiply and divide by 1000 as needed
    history = attributes.bytes(allowNone=True) # stores a pickled list

    url = attributes.bytes(allowNone=False)
    title = attributes.text()

    totalClicks = attributes.integer(default=0)
    intervalClicks = attributes.integer(default=0)
    interval = attributes.integer(default=STATS_INTERVAL) # seconds
    depth = attributes.integer(default=30)
    delta = attributes.integer(default=5)
    statKeeper = attributes.reference()

    def recordClick(self, lastInterval, now):
        self.intervalClicks += 1
        self.totalClicks += 1

        lastEnd = lastInterval.asPOSIXTimestamp()
        if now - lastEnd > self.interval:
            missedIntervals = int((now - lastEnd) / self.interval)
            hist = self.recordHistory(missedIntervals - 1)
            self.updateScore(hist)

    def recordHistory(self, pad):
        hist = _loadHistory(self.history)
        hist.extend([0] * min(pad, self.depth))
        hist.append(self.intervalClicks)
        self.intervalClicks = 1
        if len(hist) > self.depth:
            del hist[:-self.depth]
        self.history = _saveHistory(hist)
        return hist

    def updateScore(self, history):
        if len(history) >= self.delta:
            now = history[-1]
            then = history[-self.delta]
            if then:
                rateOfChange = ((now - then) / then) * 100
            elif now:
                rateOfChange =  1 / now
            else:
                rateOfChange = 0.0
            self.score = int(rateOfChange * 1000)


class AggregateClick(juice.Command):
    commandName = 'Aggregate-Click'

    arguments = [('title', juice.Unicode()),
                 ('url', juice.String())]

def nextInterval(now, interval):
    return (now // interval * interval) + interval

HISTORY_DEPTH = 25
class ClickChroniclePublicPage(Item):
    implements(ixmantissa.IPublicPage)

    typeName = 'clickchronicle_public_page'
    schemaVersion = 3

    installedOn = attributes.reference()

    clickListeners = attributes.inmemory()
    recentClicks = attributes.inmemory()
    totalClicks = attributes.integer(default=0)

    lastIntervalEnd = attributes.timestamp()
    interval = attributes.integer(default=STATS_INTERVAL) # seconds

    clickLogFile = attributes.inmemory()

    def __init__(self, **kw):
        super(ClickChroniclePublicPage, self).__init__(**kw)
        self.lastIntervalEnd = extime.Time.fromPOSIXTimestamp(nextInterval(self.time(), self.interval))

    def time(self):
        return time.time()

    def activate(self):
        self.clickListeners = []
        self.recentClicks = collections.deque()
        self.clickLogFile = self.store.newFilePath('clicks.log').open('a')

    def installOn(self, other):
        assert self.installedOn is None, "Cannot install ClickChroniclePublicPage on more than one thing"
        other.powerUp(self, ixmantissa.IPublicPage)
        self.installedOn = other

    def anonymousResource(self):
        return self.getPublicPageFactory().resourceForUser(None)

    def getPublicPageFactory(self):
        return GenericPublicPage(PublicIndexPage, self, ixmantissa.IStaticShellContent(self.installedOn, None))

    def observeClick(self, title, url):
        self.totalClicks += 1

        self.clickLogFile.write('%s %s\n' % (extime.Time().asISO8601TimeAndDate(), url))
        self.recentClicks.append((title, url))
        if len(self.recentClicks) > HISTORY_DEPTH:
            self.recentClicks.popleft()

        # XXX Desync this, it's gonna get slow.
        for listener in self.clickListeners:
            listener.observeClick(title, url)

        clickStat = self.store.findOrCreate(ClickStats, statKeeper=self, url=url, interval=self.interval)
        clickStat.title = title
        clickStat.recordClick(self.lastIntervalEnd, self.time())

        catalog = self.store.findOrCreate(Catalog)

        for tag in catalog.tagsOf(clickStat):
            break
        else:
            for tag in tagURL(url):
                catalog.tag(clickStat, tag)

        now = int(self.time())
        if now > self.lastIntervalEnd.asPOSIXTimestamp():
            self.lastIntervalEnd = extime.Time.fromPOSIXTimestamp(nextInterval(now, self.interval))

    def listenClicks(self, who):
        self.clickListeners.append(who)
        return lambda: self.clickListeners.remove(who)


class CCPublicPageMixin(object):
    navigationFragment = staticTemplate("static-nav.html")
    loggedInNavigationFragment = staticTemplate("logged-in-static-nav.html")
    title = "ClickChronicle"

    def render_head(self, ctx, data):
        yield super(CCPublicPageMixin, self).render_head(ctx, data)
        yield tags.title[self.title]
        yield tags.link(rel="stylesheet", type="text/css", href="/static/css/static-site.css")

    def render_navigation(self, ctx, data):
        if self.username is None:
            fragment = self.navigationFragment
        else:
            fragment = self.loggedInNavigationFragment

        return ctx.tag[fragment]

class CCPublicPage(CCPublicPageMixin, PublicPage):
    pass

class PublicIndexPage(CCPublicPageMixin, PublicLivePage):
    title = 'ClickChronicle'
    maxTitleLength = 50
    maxClickQueryResults = 10

    def __init__(self, original, staticContent, forUser):
        templateContent = staticTemplate("index.html")
        super(PublicIndexPage, self).__init__(original, templateContent, staticContent, forUser)
        self.clickContainerPattern = inevow.IQ(templateContent).patternGenerator('click-container')

        def mkchild(tmplname, title):
            p = CCPublicPage(original, staticTemplate(tmplname), staticContent, forUser)
            p.title = title
            return p

        self.children =  {"privacy-policy" : mkchild('privacy-policy.html',
                                                     'ClickChronicle Privacy Policy'),
                          "faq" : mkchild('faq.html', 'Clickchronicle FAQ'),
                          "screenshots" : mkchild('screenshots.html', 'ClickChronicle Screenshots')}

    def render_head(self, ctx, data):
        yield super(PublicIndexPage, self).render_head(ctx, data)
        yield makeScriptTag("/static/js/live-clicks.js")

    def goingLive(self, ctx, client):
        self.client = client
        unlisten = self.original.listenClicks(self)
        client.notifyOnClose().addCallback(lambda ign: unlisten())
        client.send([
            (livepage.js.clickchronicle_addClick(self.trimTitle(t), u), livepage.eol)
                for (t, u) in self.original.recentClicks])

    def child_(self, ctx):
        return self

    def trimTitle(self, title):
        if self.maxTitleLength < len(title):
            title = title[:self.maxTitleLength-3] + '...'
        return title

    def highestScoredByTag(self, tagName, limit=maxClickQueryResults):
        return self.original.store.query(ClickStats,
                attributes.AND(Tag.object == ClickStats.storeID,
                               Tag.name == tagName),
                sort=ClickStats.totalClicks.descending,
                limit=limit)

    def highestScored(self, limit=maxClickQueryResults):
        store = self.original.store
        return store.query(ClickStats,
                           sort=ClickStats.totalClicks.descending,
                           limit=limit)

    def asDicts(self, clickStats):
        for item in clickStats:
            yield dict(title=self.trimTitle(item.title),
                       url=item.url, clicks=item.totalClicks)

    def render_totalClicks(self, ctx, data):
        return ctx.tag[self.original.totalClicks]

    def _renderClicks(self, ctx, clicks):
        return ctx.tag[self.clickContainerPattern(data=self.asDicts(clicks))]

    def render_popularSearches(self, ctx, data):
        return self._renderClicks(ctx, self.highestScoredByTag(u'search'))

    def render_popularNews(self, ctx, data):
        return self._renderClicks(ctx, self.highestScoredByTag(u'news'))

    def render_popularClicks(self, ctx, data):
        return self._renderClicks(ctx, self.highestScored())

    def observeClick(self, title, url):
        self.client.call('clickchronicle_addClick', self.trimTitle(title), url)
        self.client.call('clickchronicle_incrementClickCounter')

# doot doot
from clickchronicle import upgraders

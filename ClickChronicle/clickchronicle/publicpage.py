# -*- test-case-name: clickchronicle.test.test_publicpage -*-

from __future__ import division

import time, struct, collections
from xmantissa.publicresource import PublicLivePage, PublicPage
from nevow import inevow, tags, livepage
from clickchronicle.util import makeScriptTag, staticTemplate
from axiom.item import Item
from axiom import attributes
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
        hist.extend([0] * pad)
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
    implements(ixmantissa.IPublicPage, inevow.IResource)

    typeName = 'clickchronicle_public_page'
    schemaVersion = 2

    installedOn = attributes.reference()

    clickListeners = attributes.inmemory()
    recentClicks = attributes.inmemory()

    lastIntervalEnd = attributes.timestamp()
    interval = attributes.integer(default=STATS_INTERVAL) # seconds

    def time(self):
        return time.time()
    
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
        if len(self.recentClicks) > HISTORY_DEPTH:
            self.recentClicks.popleft()

        # XXX Desync this, it's gonna get slow.
        for listener in self.clickListeners:
            listener.observeClick(title, url)

        clickStat = self.store.findOrCreate(ClickStats, statKeeper=self, url=url)
        clickStat.title = title
        clickStat.recordClick(self.lastIntervalEnd, self.time())

        now = int(time.time())
        if now > self.lastIntervalEnd:
            self.lastIntervalEnd = nextIntervalEnd(now, self.interval)

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

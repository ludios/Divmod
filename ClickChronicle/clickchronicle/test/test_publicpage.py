import datetime

from twisted.trial import unittest

from epsilon import extime

from axiom import store

from clickchronicle import publicpage

class IntervalTests(unittest.TestCase):
    def testNextInterval(self):
        data = [
            (105, 20, 120),
            (115, 20, 120),
            (120, 20, 140),
            (141, 20, 160),
            (160, 20, 180),
            ]
        for (now, interval, expected) in data:
            self.assertEquals(publicpage.nextInterval(now, interval), expected)

class ClickStatsTests(unittest.TestCase):
    def setUp(self):
        self.store = store.Store(self.mktemp())

    def testClickRecording(self):
        click = publicpage.ClickStats(store=self.store,
                                      url='http://example.com/test',
                                      interval=10,
                                      delta=2)

        lastInterval = extime.Time()
        now = lastInterval.asPOSIXTimestamp()

        self.assertEquals(len(publicpage._loadHistory(click.history)), 0)

        click.recordClick(lastInterval, now + 2)
        click.recordClick(lastInterval, now + 8)

        self.assertEquals(len(publicpage._loadHistory(click.history)), 0)

        self.assertEquals(click.intervalClicks, 2)
        self.assertEquals(click.totalClicks, 2)
        self.assertEquals(click.score, 0)

        # Jumping into another interval
        click.recordClick(lastInterval, now + 12)

        self.assertEquals(len(publicpage._loadHistory(click.history)), 1)

        self.assertEquals(click.intervalClicks, 1)
        self.assertEquals(click.totalClicks, 3)
        self.assertEquals(click.score, 0)

        # a value like now + 12 will only be passed to recordClick
        # immediately before lastInterval is updated.  So, we'll
        # update lastInterval here.  It advances by 10 seconds, since
        # 10 is what was passed to ClickStats' interval argument
        # above.
        lastInterval += datetime.timedelta(seconds=10)

        # And yet another interval - this time we should end up with a
        # score
        click.recordClick(lastInterval, now + 48)

        self.assertEquals(click.intervalClicks, 1)
        self.assertEquals(click.totalClicks, 4)

        self.assertEquals(len(publicpage._loadHistory(click.history)), 4)

        # This value depends upon an internal scheme - it may change
        # as we come up with better ideas.
        #self.assertEquals(click.score, -33333)

    def testClickObserving(self):
        now = 100.0
        def when(self):
            return now
        orig_time = publicpage.ClickChroniclePublicPage.time.im_func
        try:
            publicpage.ClickChroniclePublicPage.time = when
            pp = publicpage.ClickChroniclePublicPage(
                store=self.store,
                interval=10)

            L = []
            class clickObserver:
                def observeClick(title, url):
                    L.append((title, url))
                observeClick = staticmethod(observeClick)
            unobserve = pp.listenClicks(clickObserver)

            pp.observeClick(u'The Internet', 'http://internet/')

            self.assertEquals(
                L,
                [(u'The Internet', 'http://internet/')])
            # Clean up for next time
            L = []

            stats = list(self.store.query(
                publicpage.ClickStats,
                publicpage.ClickStats.statKeeper == pp))

            self.assertEquals(len(stats), 1)
            self.assertEquals(stats[0].url, 'http://internet/')
            self.assertEquals(stats[0].title, u'The Internet')
            self.assertEquals(stats[0].totalClicks, 1)
            self.assertEquals(stats[0].intervalClicks, 1)

            # Spin the clock a tiny bit for realism or something
            now = 102.0

            # Do it again!  There should still just be one StatsClick
            # instance for this URL.  Also, the title should be updated in
            # the database.
            pp.observeClick(u'Internet v2.0', 'http://internet/')

            self.assertEquals(
                L,
                [(u'Internet v2.0', 'http://internet/')])
            L = []

            stats = list(self.store.query(
                publicpage.ClickStats,
                publicpage.ClickStats.statKeeper == pp))

            self.assertEquals(len(stats), 1)
            self.assertEquals(stats[0].url, 'http://internet/')
            self.assertEquals(stats[0].title, u'Internet v2.0')
            self.assertEquals(stats[0].totalClicks, 2)
            self.assertEquals(stats[0].intervalClicks, 2)

            # Make sure unobserve works
            unobserve()

            # Make sure we bump the interval period at least once
            now = 123.4
            pp.observeClick(u'Internet v2.0', 'http://internet/')

            self.assertEquals(L, [])

            stats = list(self.store.query(
                publicpage.ClickStats,
                publicpage.ClickStats.statKeeper == pp))

            self.assertEquals(len(stats), 1)
            self.assertEquals(stats[0].url, 'http://internet/')
            self.assertEquals(stats[0].title, u'Internet v2.0')
            self.assertEquals(stats[0].totalClicks, 3)
            self.assertEquals(stats[0].intervalClicks, 1)
        finally:
            publicpage.ClickChroniclePublicPage.time = orig_time

    testClickObserving.todo = testClickRecording.todo = 'reinstate last interval argument to recordClick, see ticket #292'

    def testTagPopularity(self):
        pp = publicpage.ClickChroniclePublicPage(store=self.store)
        pp.installOn(self.store)
        # just a simple sanity check until we add configurable
        # tag-assigners
        clicks = list(pp.highestScoredByTag(unicode(self.mktemp()), limit=1))
        self.assertEqual(clicks, [])
        pp.observeClick(u'Google', 'http://www.google.com/search?q=hello+world')
        clicks = list(pp.highestScoredByTag(unicode(self.mktemp()), limit=1))
        self.assertEqual(clicks, [])

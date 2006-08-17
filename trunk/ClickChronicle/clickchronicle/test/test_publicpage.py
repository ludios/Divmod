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
        orig_getInterval = publicpage.ClickStats._getInterval
        try:
            publicpage.ClickStats._getInterval = lambda self: 10
            click = publicpage.ClickStats(store=self.store,
                                          url='http://example.com/test')

            now = extime.Time.fromPOSIXTimestamp(11)
            def future(n):
                return now + datetime.timedelta(seconds=n)

            self.assertEquals(len(publicpage._loadHistory(click.history)), 0)

            click.recordClick(future(2))
            click.recordClick(future(8))

            self.assertEquals(len(publicpage._loadHistory(click.history)), 1)

            self.assertEquals(click.intervalClicks, 2)
            self.assertEquals(click.totalClicks, 2)
            #self.assertEquals(click.score, 0)

            # Jumping into another interval
            click.recordClick(future(12))

            self.assertEquals(len(publicpage._loadHistory(click.history)), 2)

            self.assertEquals(click.intervalClicks, 1)
            self.assertEquals(click.totalClicks, 3)

            # Make sure no numbers change
            click.recordClick(future(12), increment=False)

            self.assertEquals(len(publicpage._loadHistory(click.history)), 2)

            self.assertEquals(click.intervalClicks, 1)
            self.assertEquals(click.totalClicks, 3)

            #self.assertEquals(click.score, 0)

            # And yet another interval - this time we should end up
            # with score
            click.recordClick(future(23))

            self.assertEquals(click.intervalClicks, 1)
            self.assertEquals(click.totalClicks, 4)

            self.assertEquals(len(publicpage._loadHistory(click.history)), 3)

            # This value depends upon an internal scheme - it may change
            # as we come up with better ideas.
            #self.assertEquals(click.score, -33333)
        finally:
            publicpage.ClickStats._getInterval = orig_getInterval


    def testClickIntervalTracking(self):
        click1 = publicpage.ClickStats(store=self.store,
                                       url='http://example.com/one',
                                       depth=5)

        click2 = publicpage.ClickStats(store=self.store,
                                       url='http://example.com/two',
                                       depth=5)

        orig_getInterval = publicpage.ClickStats._getInterval
        try:
            publicpage.ClickStats._getInterval = lambda self: 10

            now = extime.Time.fromPOSIXTimestamp(11)
            def future(n):
                return now + datetime.timedelta(seconds=n)

            click1.recordClick(future(0))       # C1
            click2.recordClick(future(5))       # C2
            click2.recordClick(future(15))      # C3
            click2.recordClick(future(16))      # C4
            click2.recordClick(future(25))      # C5
            click1.recordClick(future(35))      # C6
            click2.recordClick(future(35))      # C7

            h1 = publicpage._loadHistory(click1.history)
            h2 = publicpage._loadHistory(click2.history)

            self.assertEquals(
                h1,
                [0,
                 1, # C1
                 0, # C3
                 0, # C5
                 ])

            self.assertEquals(click1.intervalClicks, 1)

            self.assertEquals(
                h2,
                [0,
                 1, # C2
                 2, # C3, C4
                 1, # C5
                 ])

            self.assertEquals(click2.intervalClicks, 1)

        finally:
            publicpage.ClickStats._getInterval = orig_getInterval

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
            self.assertEquals(pp.lowestPopularScore, 0)
            L = []
            class clickObserver:
                def observeClick(title, url):
                    L.append((title, url))
                observeClick = staticmethod(observeClick)
            unobserve = pp.listenClicks(clickObserver, 'all')

            pp.observeClick(u'The Internet', 'http://internet/')
            pp.observeClick(u'The Internet2', 'http://internet2/')

            self.assertEquals(
                L,
                [(u'The Internet', 'http://internet/'),
                 (u'The Internet2', 'http://internet2/'),])
            # Clean up for next time
            L = []

            stats = list(self.store.query(
                publicpage.ClickStats,
                publicpage.ClickStats.statKeeper == pp))

            self.assertEquals(len(stats), 2)
            self.assertEquals(stats[0].url, 'http://internet/')
            self.assertEquals(stats[1].url, 'http://internet2/')
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

            self.assertEquals(len(stats), 2)
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

            self.assertEquals(len(stats), 2)
            self.assertEquals(stats[0].url, 'http://internet/')
            self.assertEquals(stats[0].title, u'Internet v2.0')
            self.assertEquals(stats[0].totalClicks, 3)
            self.assertEquals(stats[0].intervalClicks, 1)
            # Adding the latest click should trigger recalculation of
            # scores for top 25 clicks. Make sure they both have a
            # non-zero score
            for stat in stats:
                self.assertNotEqual(stat.score, 0)

            stats = list(self.store.query(
                publicpage.ClickStats,
                publicpage.ClickStats.statKeeper == pp,
                sort=publicpage.ClickStats.score.descending,))
            self.assertEquals(len(stats),2)
            self.assertEquals(stats[0].url, 'http://internet/')
            self.assertEquals(stats[1].url, 'http://internet2/')
        finally:
            publicpage.ClickChroniclePublicPage.time = orig_time

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

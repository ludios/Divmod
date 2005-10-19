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
        self.store = store.Store()

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
        click.recordClick(lastInterval, now + 23)

        self.assertEquals(click.intervalClicks, 1)
        self.assertEquals(click.totalClicks, 4)

        self.assertEquals(len(publicpage._loadHistory(click.history)), 2)

        # This value depends upon an internal scheme - it may change
        # as we come up with better ideas.
        self.assertEquals(click.score, -33333)

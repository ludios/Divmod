from twisted.application.service import IService
from twisted.trial.unittest import TestCase
from twisted.trial.util import wait
from twisted.web.error import Error
from nevow.url import URL
from clickchronicle import iclickchronicle
from clickchronicle.clickapp import ClickRecorder
from clickchronicle.visit import Visit, Domain, BookmarkVisit, Bookmark
from clickchronicle.test.base import CCTestBase

allTitles = lambda visits: (v.title for v in visits)

class ClickRecorderTestCase(CCTestBase, TestCase):
    def setUpClass(self):
        self.setUpStore()

    def tearDown(self):
        for visit in self.substore.query(Visit):
            self.recorder.forgetVisit(visit)

        for cls in (Domain, Bookmark):
            for item in self.substore.query(cls):
                item.deleteFromStore()

    def testRecord(self):
        self.assertNItems(self.substore, Visit, 0)
        self.assertNItems(self.substore, Domain, 0)

        url = self.randURL()
        self.makeVisit(url=url, title=self.mktemp(), indexIt=False)
        nextUrl = str(URL.fromString(url).child('a').child('b'))
        # different URL, same hostname, different title
        self.makeVisit(url=nextUrl, title=self.mktemp(), indexIt=False)
        # same URL, different title
        self.makeVisit(url=nextUrl, title=self.mktemp(), indexIt=False)

    def _testBookmark(self):
        ss = self.substore

        self.assertNItems(ss, Visit, 0)
        self.assertNItems(ss, Domain, 0)
        self.assertNItems(ss, Bookmark, 0)

        url = self.randURL()
        visit = self.makeVisit(url=url, title=self.mktemp(), indexIt=False)
        def _():
            return visit.asBookmark()
        bm = ss.transact(_)
        self.assertNItems(ss, Bookmark, 1)
        self.assertEqual(visit.url, bm.url)
        self.assertEqual(visit.domain, bm.domain)

    def testReferrer(self):
        iterurls = self.urlsWithSameDomain()
        url = iterurls.next()
        visit = self.record(title=url, url=url)
        # better way to do this comparison?
        self.assertEqual(visit.referrer.typeName, BookmarkVisit.typeName)
        refereeUrl = iterurls.next()
        refereeVisit = self.record(title=refereeUrl, url=refereeUrl, ref=url)
        self.assertEqual(refereeVisit.referrer.url, visit.url)

    def _testDeletionOfOldestVisit(self, maxCount=5):
        self.recorder.deleteFromStore()
        del self.recorder # i _hate_ statements
        self.recorder = ClickRecorder(store=self.substore, maxCount=maxCount)
        self.recorder.installOn(self.substore)
        urls = list(self.urlsWithSameDomain(count=maxCount+1))

        def storeAndCheck(url, nth):
            self.record(title=url, url=url)
            self.assertNItems(self.substore, Visit, nth)
            self.assertEqual(self.recorder.visitCount, nth)

        for i in xrange(maxCount):
            storeAndCheck(urls[i], i+1)

        def orderedTitles():
            return list(allTitles(self.substore.query(Visit,
                            sort=Visit.timestamp.ascending)))

        allTitlesOrdered = orderedTitles()
        urls = sorted(urls)
        self.assertEqual(sorted(allTitlesOrdered), urls[:maxCount])
        storeAndCheck(urls[-1], maxCount)
        oldestTitle = allTitlesOrdered[0]
        urls.remove(oldestTitle)
        self.assertEqual(sorted(orderedTitles()), urls)


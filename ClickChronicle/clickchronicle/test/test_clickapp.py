from twisted.trial.unittest import TestCase
from nevow.url import URL
from axiom.dependency import installOn, uninstallFrom
from clickchronicle.clickapp import ClickRecorder
from clickchronicle.visit import Visit, Domain, BookmarkVisit, Bookmark
from clickchronicle.test.base import CCTestBase

allTitles = lambda visits: (v.title for v in visits)

class ClickRecorderTestCase(CCTestBase, TestCase):
    def setUp(self):
        self.setUpStore()

    def tearDown(self):
        def txn():
            for visit in self.substore.query(Visit):
                self.recorder.forgetVisit(visit)

            for cls in (Domain, Bookmark):
                for item in self.substore.query(cls):
                    item.deleteFromStore()

        self.substore.transact(txn)

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

    def testBookmark(self):
        visit = self.makeVisit(url=self.randURL(), title=self.mktemp(), indexIt=False)

        bookmark = visit.asBookmark()

        self.assertNItems(self.substore, Bookmark, 1)

        self.assertEqual(bookmark.visitCount, visit.visitCount)
        self.assertEqual(visit.url, bookmark.url)
        self.assertEqual(visit.domain, bookmark.domain)

    def testReferrer(self):
        iterurls = self.urlsWithSameDomain()
        url = iterurls.next()
        visit = self.record(title=url, url=url)
        self.assertEqual(visit.referrer.typeName, BookmarkVisit.typeName)
        refereeUrl = iterurls.next()
        refereeVisit = self.record(title=refereeUrl, url=refereeUrl, ref=url)
        self.assertEqual(refereeVisit.referrer.url, visit.url)

    def testDeletionOfOldestVisit(self, maxCount=5):
        uninstallFrom(self.recorder, self.substore)
        self.recorder.deleteFromStore()
        del self.recorder

        self.recorder = ClickRecorder(store=self.substore, maxCount=maxCount)
        installOn(self.recorder, self.substore)
        urls = list(self.urlsWithSameDomain(count=maxCount+1))

        limitUrls = urls[:-1]
        for url in limitUrls:
            self.record(url=url, title=self.mktemp(), indexIt=False)
        self.assertNItems(self.substore, Visit, maxCount)

        visitsByAge = list(self.substore.query(Visit, sort=Visit.timestamp.ascending))
        self.assertEqual(sorted(limitUrls), sorted(visit.url for visit in visitsByAge))

        self.record(url=urls[-1], title=self.mktemp(), indexIt=False)
        self.assertNItems(self.substore, Visit, maxCount)

        expectedUrls = list(v.url for v in visitsByAge[1:]) + urls[-1:]
        self.assertEqual(sorted(expectedUrls), sorted(visit.url for visit in self.substore.query(Visit)))

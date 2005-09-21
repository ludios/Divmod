from tempfile import mktemp
from twisted.trial.unittest import TestCase
from twisted.trial.util import wait
from twisted.web.error import Error
from nevow.url import URL
from clickchronicle.visit import Visit, Domain, BookmarkVisit
from clickchronicle.test.base import (IndexAwareTestBase, 
                                      MeanResourceTestBase, 
                                      CCTestBase)

class ClickRecorderTestCase(CCTestBase, TestCase):
    def setUpClass(self):
        self.setUpStore()

    def testRecordNoIndex(self):
        ss = self.substore
        
        self.assertNItems(ss, Visit, 0)
        self.assertNItems(ss, Domain, 0)
      
        url = self.randURL()
        wait(self.makeVisit(url=url, title=mktemp(), index=False))
        nextUrl = str(URL.fromString(url).child('a').child('b'))
        # different URL, same hostname, different title
        wait(self.makeVisit(url=nextUrl, title=mktemp(), index=False))
        # same URL, different title
        wait(self.makeVisit(url=nextUrl, title=mktemp(), index=False))

    def testReferrer(self):
        iterurls = self.urlsWithSameDomain()
        url = iterurls.next()
        visit = self.record(title=url, url=url)
        # better way to do this comparison?
        self.assertEqual(visit.referrer.typeName, BookmarkVisit.typeName)
        refereeUrl = iterurls.next()
        refereeVisit = self.record(title=refereeUrl, url=refereeUrl, ref=url)
        self.assertEqual(refereeVisit.referrer.url, visit.url)
        
class IgnoreDomainTestCase(CCTestBase, TestCase):

    def setUp(self):
        self.setUpStore()

    def testIgnoreVisitIgnoresDomain(self):
        url = self.randURL()
        visit = self.record(title=url, url=url) 
        domain = visit.domain
        self.ignore(visit)
        self.assertEqual(domain.ignore, 1)

    def testVisitsToIgnoredDomains(self):
        iterurls = self.urlsWithSameDomain()
        url = iterurls.next()
        self.ignore(self.record(title=url, url=url))
        self.assertNItems(self.substore, Visit, 0)
        self.assertEqual(self.recorder.visitCount, 0)
        for url in iterurls:
            self.record(title=url, url=url)
            self.assertNItems(self.substore, Visit, 0)
            self.assertEqual(self.recorder.visitCount, 0)

    def testIgnoreVisitIgnoresOldVisits(self):
        # visitURLs wants a title -> url dictionary
        urls = dict((u, u) for u in self.urlsWithSameDomain())
        
        def afterVisits():
            self.assertEqual(self.recorder.visitCount, len(urls))
            self.assertNItems(self.substore, Visit, len(urls))
            visit = self.firstItem(self.substore, Visit)
            self.ignore(visit)
            self.assertEqual(self.recorder.visitCount, 0)
            self.assertNItems(self.substore, Visit, 0)

        return self.visitURLs(urls, index=False).addCallback(lambda ign: afterVisits())
            
allTitles = lambda visits: (v.title for v in visits)

class IndexingClickRecorderTestCase(IndexAwareTestBase, TestCase):
    def setUpClass(self):
        self.setUpWebIndexer()
        return self.visitURLs(self.urls)

    def tearDownClass(self):
        self.tearDownWebIndexer()

    def testCommonTermsMatchAll(self):
        data = dict((k, v.data) for (k, v) in self.resourceMap.iteritems())

        (first, second) = (data['first'], data['second'])
        
        self.assertUniform(('first', 'both'),
                           *(allTitles(self.itemsForTerm(t)) for t in first.split()))
        
        self.assertUniform(('second', 'both'),
                           *(allTitles(self.itemsForTerm(t)) for t in second.split()))
        
    def testNonUniversalTermsDontMatchAll(self):
        both = self.resourceMap['both'].data
        self.assertUniform(allTitles(self.itemsForTerm('a i')), ('both',))
        self.assertUniform(allTitles(self.itemsForTerm(both)), ('both',))

    def testCounterfeitMatches(self):
        self.assertEqual(len(list(self.itemsForTerm('z'))), 0)
        self.assertEqual(len(list(self.itemsForTerm('xyz'))), 0)

    def testForgottenVisitsDontMatch(self):
        both = self.substore.query(Visit, Visit.title=='both').next()
        self.recorder.forgetVisit(both)
        # we've removed the "both" visit - nothing should match terms
        # containing exclusive tokens from multiple visits
        self.assertEqual(len(list(self.itemsForTerm('a i'))), 0)
        # i am the only test method that modifies the store, so i'll recreate
        # it after i'm done so as not to affect the other tests.  we could
        # do everything in setUp() and tearDown() but my laptop is old and
        # slow and setUpStore() takes a really long time to run
        self.tearDownClass(); return self.setUpClass()

class MeanResourceTestCase(MeanResourceTestBase, TestCase):
    def setUp(self):
        self.setUpWebIndexer()

    def tearDown(self):
        self.tearDownWebIndexer()
        
    def testNoRecord(self):
        def onRecordingError(f):
            f.trap(Error)
            # assert nothing was indexed
            self.assertEqual(preIndexCount, self.indexer.indexCount)
            # assert a visit was created
            self.assertEqual(preVisitCount+1, self.recorder.visitCount)
            self.assertNItems(self.substore, Visit, 1)
            visit = self.firstItem(self.substore, Visit)
            self.recorder.forgetVisit(visit)
            self.assertNItems(self.substore, Visit, 0)
            self.assertEqual(preVisitCount, self.recorder.visitCount)

        self.assertNItems(self.substore, Visit, 0)
        preIndexCount = self.indexer.indexCount
        self.assertEqual(preIndexCount, 0)
        preVisitCount = self.recorder.visitCount
        self.assertEqual(preVisitCount, 0)
        futureSuccess = self.recorder.recordClick(dict(url=self.urls['mean'], 
                                                       title='mean'), index=True)
        
        return futureSuccess.addCallbacks(lambda ign: self.fail('expected 400 "BAD REQUEST"'),
                                          onRecordingError)

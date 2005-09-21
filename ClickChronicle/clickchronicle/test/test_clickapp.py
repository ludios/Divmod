from tempfile import mktemp
from twisted.trial.unittest import TestCase
from twisted.trial.util import wait
from nevow.url import URL
from twisted.internet import defer
from clickchronicle.visit import Visit, Domain
from clickchronicle.test.base import (IndexAwareTestBase, MeanResourceTestBase, 
                                      CCTestBase, firstItem)

class ClickRecorderTestCase(CCTestBase, TestCase):
    def setUp(self):
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

allTitles = lambda visits: (v.title for v in visits)

class IndexingClickRecorderTestCase(IndexAwareTestBase, TestCase):
    
    def setUpClass(self):
        IndexAwareTestBase.setUpClass(self)
        deferreds = []
        for (resname, url) in self.urls.iteritems():
            futureVisit = self.recorder.recordClick(dict(url=url, title=resname), index=True)
            deferreds.append(futureVisit)
        return defer.gatherResults(deferreds)

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
    
    def testNoRecord(self):
        def onRecordingError():
            # assert nothing was indexed
            self.assertEqual(preIndexCount, self.indexer.indexCount)
            # assert a visit was created
            self.assertEqual(preVisitCount+1, self.recorder.visitCount)
            self.assertNItems(self.substore, Visit, 1)
            visit = firstItem(self.substore, Visit)
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
        return futureSuccess.addCallbacks(lambda ign: self.fail('expected BAD REQUEST'),
                                          lambda ign: onRecordingError())


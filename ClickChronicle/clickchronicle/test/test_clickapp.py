from tempfile import mktemp
from twisted.trial.unittest import TestCase
from twisted.trial.util import wait
from nevow.url import URL
from twisted.internet import defer
from clickchronicle.visit import Visit, Domain
from clickchronicle.test.base import DataServingTestBase, CCTestBase, firstPowerup
from clickchronicle.indexinghelp import IIndexer

class ClickRecorderTestCase(CCTestBase):# TestCase):
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

class IndexingClickRecorderTestCase(DataServingTestBase, TestCase):
    def setUpClass(self):
        DataServingTestBase.setUpClass(self)
        self.setUpStore()
        self.indexer = firstPowerup(self.substore, IIndexer)
        # set up a webserver with three resources
        first  = 'a b c d e f g h'
        second = 'i j k l m n o p'
        union = ' '.join((first, second))
        # GET /first will return "a b c d e f g h", etc
        self.data = dict(first=first, second=second, union=union)
        self.urls = self.serve(self.data)

        self.visits = dict()
        for (resname, url) in self.urls.iteritems():
            self.visits[resname] = wait(self.makeVisit(url=url, title=resname, index=True))

    def setUp(self):
        pass

    def itemsForTerm(self, term):
        return (self.substore.getItemByID(d['uid']) for d in self.indexer.search(term))
    
    def testCommonTermsMatchAll(self):
        (first, second) = (self.data['first'], self.data['second'])
        
        self.assertUniform(('first', 'union'),
                           *(allTitles(self.itemsForTerm(t)) for t in first.split()))
        
        self.assertUniform(('second', 'union'),
                           *(allTitles(self.itemsForTerm(t)) for t in second.split()))
        
    def testNonUniversalTermsDontMatchAll(self):
        union = self.data['union']
        self.assertUniform(allTitles(self.itemsForTerm('a i')), ('union',))
        self.assertUniform(allTitles(self.itemsForTerm(union)), ('union',))

    def testCounterfeitMatches(self):
        # check we don't have any counterfeit matches
        self.assertEqual(len(list(self.itemsForTerm('z'))), 0)
        self.assertEqual(len(list(self.itemsForTerm('xyz'))), 0)

    def _testForgottenVisitsDontMatch(self):
        self.recorder.forgetVisit(self.visits['union'])
        # we've removed the "union" visit - nothing should match terms
        # containing exclusive tokens from multiple visits
        self.assertEqual(len(list(self.itemsForTerm('a i'))), 0)
        # i am the only test method that modifies the store, so i'll recreate
        # it after i'm done so as not to affect the other tests
        self.setUpStore(); self.visit(self.urls)

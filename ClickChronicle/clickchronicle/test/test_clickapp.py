from twisted.python.util import sibpath
from clickchronicle import clickapp
from clickchronicle.visit import Visit, Domain
from twisted.trial.unittest import TestCase
from xmantissa import signup
from axiom.store import Store
from axiom.userbase import LoginSystem
from nevow.url import URL
from tempfile import mktemp

itemCount = lambda store, item: len(list(store.query(item)))
firstItem = lambda store, item: store.query(item).next()

class SignupTestBase:
    storeLoc = 'teststore'
    
    def setUp(self):
        store = Store(self.storeLoc)
        LoginSystem(store = store).installOn(store)
        benefactor = clickapp.ClickChronicleBenefactor(store = store)
        booth = signup.TicketBooth(store = store)
        booth.installOn(store)
        ticket = booth.createTicket(booth, u'x@y.z', benefactor)
        ticket.claim()
        self.superstore = store
        self.substore = ticket.avatar.avatars.substore

class ClickRecorderTestCase(SignupTestBase, TestCase):
    def assertNItems(self, store, item, count):
        self.assertEqual(itemCount(store, item), count)

    def randURL(self):
        return '%s.com' % mktemp(dir='http://', suffix='/')

    def makeVisit(self, url='http://some.where', title='Some Where',
                  recorder=None, clicklist=None):

        host = URL.fromString(url).netloc
        for domain in self.substore.query(Domain, Domain.host==host):
            domainCount = domain.visitCount
            break
        else:
            domainCount = 0
        
        (seenURL, visitCount, prevTitle) = (False, 0, None)
        for visit in self.substore.query(Visit, Visit.url==url):
            (seenURL, visitCount, prevTitle) = (True, visit.visitCount, visit.title)
            break

        if recorder is None:
            recorder = firstItem(self.substore, clickapp.ClickRecorder)
        if clicklist is None:
            clicklist = firstItem(self.substore, clickapp.ClickList)
            
        preClicks = clicklist.clicks
        recorder.recordClick(dict(url=url, title=title), index=False)
        if not seenURL:
            self.assertEqual(clicklist.clicks, preClicks+1)

        visit = self.substore.query(Visit, Visit.url==url).next()
        self.assertEqual(visit.visitCount, visitCount+1)
        
        if seenURL:
            self.assertEqual(visit.title, prevTitle)
        else:
            self.assertEqual(visit.title, title)

        self.assertEqual(visit.domain.visitCount, domainCount+1)
        self.assertEqual(visit.domain.host, host)
            
        return visit    

    def testRecord(self):
        # this is marginally unpleasant - i cannot think of a way to change
        # the page-source-getting function that Visit uses (to make the test
        # not make http requests) without either making a new Visit item
        # definition inside this test, or making a new benefactor inside this
        # test, both are pretty crap choices.  so i added an "index" kwarg to
        # recordClick.  this isn't much better b/c we cant return arbitrary
        # content to the indexer.  any ideas?
        ss = self.substore
        (recorder, clicklist) = (firstItem(ss, clickapp.ClickRecorder),
                                 firstItem(ss, clickapp.ClickList))
        _makeVisit = lambda *a, **k: self.makeVisit(recorder=recorder, 
                                                    clicklist=clicklist, *a, **k)
        
        self.assertNItems(self.substore, Visit, 0)
        self.assertNItems(self.substore, Domain, 0)
       
        v1 = _makeVisit(url=self.randURL(), title=mktemp())
        nextUrl = str(URL.fromString(v1.url).child('a').child('b'))
        # different URL, same hostname, different title
        v2 = _makeVisit(url=nextUrl, title=mktemp())
        # same URL, different title
        v3 = _makeVisit(url=nextUrl, title=mktemp())

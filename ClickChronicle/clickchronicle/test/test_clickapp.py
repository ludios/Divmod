from twisted.python.util import sibpath
from clickchronicle import clickapp
from clickchronicle.visit import Visit, Domain
from twisted.trial.unittest import TestCase
from xmantissa import signup
from axiom.store import Store
from axiom.userbase import LoginSystem

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
        
    def testRecord(self):
        recorder = firstItem(self.substore, clickapp.ClickRecorder)
        # this is marginally unpleasant - i cannot think of a way to change
        # the page-source-getting function that Visit uses (to make the test
        # not make http requests) without either making a new Visit item
        # definition inside this test, or making a new benefactor inside this
        # test, both are pretty crap choices.  so i added an "index" kwarg to
        # recordClick.  any ideas?
        
        visitAttrs = dict(url='http://first.click', title='First Click')
        
        self.assertNItems(self.substore, Visit, 0)
        self.assertNItems(self.substore, Domain, 0)
        
        recorder.recordClick(visitAttrs, index=False) 
        
        self.assertNItems(self.substore, Visit, 1)
        self.assertNItems(self.substore, Domain, 1)
        
        firstVisit = firstItem(self.substore, Visit)
        self.assertEqual(firstVisit.url, visitAttrs['url'])
        self.assertEqual(firstVisit.title, visitAttrs['title'])
        self.assertEqual(firstVisit.visitCount, 1)
        self.failUnless(firstVisit.referrer is None, 'expected None for Visit.referrer') 
        
        self.assertEqual(firstVisit.domain.host, firstVisit.url[len('http://'):])
        self.assertEqual(firstVisit.domain.title, firstVisit.domain.host)
        self.assertEqual(firstVisit.domain.ignore, 0)
        self.assertEqual(firstVisit.domain.visitCount, firstVisit.visitCount)


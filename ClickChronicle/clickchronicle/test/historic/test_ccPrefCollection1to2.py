
from axiom.test.historic import stubloader
from clickchronicle import clickapp

from twisted.application.service import IService

class CCPrefCollectionTestCase(stubloader.StubbedTest):
    def setUp(self):
        stubloader.StubbedTest.setUp(self)
        self.service = IService(self.store)
        self.service.startService()
        return self.store.whenFullyUpgraded()


    def tearDown(self):
        return self.service.stopService()


    def testUpgrade(self):
        pc = self.store.findUnique(clickapp.CCPreferenceCollection)
        self.failUnless(pc.shareClicks)
        self.failUnless(hasattr(pc, 'getSections'))

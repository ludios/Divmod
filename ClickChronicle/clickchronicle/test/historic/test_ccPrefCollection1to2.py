
from axiom.test.historic import stubloader
from clickchronicle import clickapp

from twisted.application.service import IService

class CCPrefCollectionTestCase(stubloader.StubbedTest):
    def testUpgrade(self):
        s = self.store
        svc = IService(s)
        svc.startService()
        D = s.whenFullyUpgraded()
        def txn(_):
            pc = s.findUnique(clickapp.CCPreferenceCollection)
            self.failUnless(pc.shareClicks)
            self.failUnless(hasattr(pc, 'getSections'))
        return D.addCallback(txn)

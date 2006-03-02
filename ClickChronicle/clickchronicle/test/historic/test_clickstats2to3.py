
from axiom.test.historic import stubloader
from clickchronicle import publicpage

from twisted.application.service import IService

class ScoreMajig(stubloader.StubbedTest):
    def setUp(self):
        stubloader.StubbedTest.setUp(self)
        self.service = IService(self.store)
        self.service.startService()
        return self.store.whenFullyUpgraded()


    def tearDown(self):
        return self.service.stopService()


    def testUpgrade(self):
        cs = self.store.findUnique(publicpage.ClickStats)
        self.failUnless(0  < cs.score, 'the score should be AT LEAST bigger than zero!!')

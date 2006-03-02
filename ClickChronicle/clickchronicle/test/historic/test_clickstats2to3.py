
from axiom.test.historic import stubloader
from clickchronicle import publicpage

from twisted.application.service import IService

class ScoreMajig(stubloader.StubbedTest):
    def testUpgrade(self):
        s = self.store
        svc = IService(s)
        svc.startService()
        D = s.whenFullyUpgraded()
        def _(fu):
            cs = s.findUnique(publicpage.ClickStats)
            self.failUnless(0  < cs.score, 'the score should be AT LEAST bigger than zero!!')
        return D.addCallback(_)


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
            self.assertEquals(cs.score, sum(publicpage._expDecay([1, 2, 3])))
        return D.addCallback(_)

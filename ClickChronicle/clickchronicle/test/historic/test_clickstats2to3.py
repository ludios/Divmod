
from axiom.test.historic import stubloader
from clickchronicle import publicpage

class ScoreMajig(stubloader.StubbedTest):
    def testUpgrade(self):
        cs = self.store.findUnique(publicpage.ClickStats)
        self.failUnless(0  < cs.score, 'the score should be AT LEAST bigger than zero!!')

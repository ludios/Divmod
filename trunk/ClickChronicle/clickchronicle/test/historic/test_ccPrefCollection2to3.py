
from axiom.test.historic import stubloader
from clickchronicle import clickapp

class CCPrefCollectionTestCase(stubloader.StubbedTest):
    def testUpgrade(self):
        pc = self.store.findUnique(clickapp.CCPreferenceCollection)
        self.failUnless(pc.shareClicks)
        self.failUnless(isinstance(pc.clicklist, clickapp.ClickList))


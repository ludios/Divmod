
from axiom.test.historic.stubloader import StubbedTest

from clickchronicle.clickapp import CCPreferenceCollection
from clickchronicle.iclickchronicle import IClickList

from xmantissa import sharing

class TestClickListStillShared(StubbedTest):
    def testClickListStillShared(self):
        self.assertEqual(
            self.store.findUnique(CCPreferenceCollection).publicPage,
            True)
        shareProxy = sharing.getShare(self.store,
                                      sharing.getEveryoneRole(self.store),
                                      u'clicks')

        self.assertEqual(shareProxy.clicks, 0)
        self.assertIn(IClickList, shareProxy.sharedInterfaces)

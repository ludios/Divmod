from twisted.trial.unittest import TestCase
from clickchronicle.visit import Visit
from clickchronicle.test.base import IndexAwareTestBase
import os

class CacheFileAwareIndexingTestCase(IndexAwareTestBase, TestCase):
    def setUp(self):
        self.setUpWebIndexer()
        self.setUpCaching()

    def tearDown(self):
        self.tearDownWebIndexer()

    def testCacheFileCreation(self):
        def afterVisitAll():
            for (i, visit) in enumerate(self.substore.query(Visit)):
                cachedFilename = self.cacheMan.cachedFileNameFor(visit)
                self.failUnless(os.path.exists(cachedFilename.path), 'bad cache filename')
                cachedText = file(cachedFilename.path).read()
                # resourceData = the text served by the resource at the
                # visit's url (we control this)
                resourceData = self.resourceMap[visit.title].data
                self.assertEqual(resourceData, cachedText)
                # now delete the visit!
                self.recorder.forgetVisit(visit)
                # and hope the cached file got removed as well
                self.failIf(os.path.exists(cachedFilename.path), 'cached file didnt get removed')
                cachedFiles = len(os.listdir(cachedFilename.parent().path))
                self.assertEqual(cachedFiles, len(self.urls)-(i+1))
            self.assertEqual(cachedFiles, 0)

        self.assertNItems(self.substore, Visit, 0)
        return self.visitURLs(self.urls).addCallback(lambda ign: afterVisitAll())

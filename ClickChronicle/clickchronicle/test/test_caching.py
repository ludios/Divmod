from tempfile import mktemp
from twisted.trial.unittest import TestCase
from twisted.trial.util import wait
from nevow.url import URL
from twisted.internet import defer
from clickchronicle.visit import Visit, Domain
from clickchronicle.test.base import IndexAwareTestBase
from os import path as osp

class CacheFileAwareIndexingTestCase(IndexAwareTestBase, TestCase):
    def setUpClass(self):
        IndexAwareTestBase.setUpClass(self)
    
    def testCacheFileCreation(self):
        def afterVisitAll():
            for (i, visit) in enumerate(self.substore.query(Visit)):
                cachedFilename = self.recorder.cachedFileNameFor(visit).path
                self.failUnless(osp.exists(cachedFilename), 'bad cache filename')
                cachedText = file(cachedFilename).read()
                # resourceData = the text served by the resource at the 
                # visit's url (we control this)
                resourceData = self.resourceMap[visit.title].data
                self.assertEqual(resourceData, cachedText)
                # now delete the visit!
                self.recorder.forgetVisit(visit)
                # and hope the cached file got removed as well
                self.failIf(osp.exists(cachedFilename), 'cached file didnt get removed')
            
        self.assertNItems(self.substore, Visit, 0)
        return self.visitURLs(self.urls).addCallback(lambda ign: afterVisitAll())
        
        

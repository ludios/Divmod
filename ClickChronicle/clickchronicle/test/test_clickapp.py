from tempfile import mktemp

from twisted.trial.unittest import TestCase
from twisted.trial.util import wait
from nevow.url import URL
from twisted.internet import defer
from clickchronicle.visit import Visit, Domain
from clickchronicle.test.base import DataServingTestBase

class ClickRecorderTestCase(DataServingTestBase, TestCase):
    def testRecordNoIndex(self):
        ss = self.substore
        
        self.assertNItems(ss, Visit, 0)
        self.assertNItems(ss, Domain, 0)
      
        url = self.randURL()
        wait(self.makeVisit(url=url, title=mktemp(), index=False))
        nextUrl = str(URL.fromString(url).child('a').child('b'))
        # different URL, same hostname, different title
        wait(self.makeVisit(url=nextUrl, title=mktemp(), index=False))
        # same URL, different title
        wait(self.makeVisit(url=nextUrl, title=mktemp(), index=False))

    def testRecordIndex(self):
        first  = 'a b c d e f g h'
        second = 'i j k l m n o p'
        both = ' '.join((first, second))
        
        data = dict(first=first, second=second, both=both)
        urls = self.serve(data)
        visits = dict()
        for (resname, url) in urls.iteritems():
            visits[resname] = wait(self.makeVisit(url=url, title=resname, index=True))

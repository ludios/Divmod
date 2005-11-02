from twisted.trial.util import wait
from twisted.internet import reactor, defer
from clickchronicle import iclickchronicle, clickapp
from clickchronicle.visit import Visit, Domain
from clickchronicle.indexinghelp import IIndexer, ICache
from xmantissa import signup
from axiom.store import Store
from axiom.scripts import axiomatic
from axiom.userbase import LoginSystem
from nevow.url import URL
from tempfile import mktemp
from twisted.web import server, resource, static, http

class CCTestBase:
    itemCount = lambda self, store, item: store.count(item)
    firstItem = lambda self, store, item: store.findFirst(item)
    firstPowerup = lambda self, store, iface: iter(store.powerupsFor(iface)).next()

    def setUpStore(self):
        """
        I set up a temporary store & substore  call me in setUp or
        setUpClass, depending on your requirements (if you have lots of test
        methods that dont modify the store, I won't need to be recreated
        before each one).
        """
        dbpath = self.mktemp()
        axiomatic.main(['-d', dbpath, 'click-chronicle-site', 'install'])
        store = Store(dbpath)

        for booth in store.query(signup.TicketBooth):
            break
        else:
            raise RuntimeError("Failed to find TicketBooth, cannot set up tests")

        for benefactor in store.query(clickapp.ClickChronicleBenefactor):
            break
        else:
            raise RuntimeError("Failed to find ClickChronicleBenefactor, cannot set up tests")

        ticket = booth.createTicket(booth, u'x@y.z', benefactor)
        ticket.claim()

        self.superstore = store
        self.substore = ticket.avatar.avatars.substore

        init = self.substore.findFirst(clickapp.ClickChronicleInitializer)
        init.setPassword('123pass456')

        self.recorder = self.firstItem(self.substore, clickapp.ClickRecorder)
        self.recorder.caching = False
        self.clicklist = self.firstItem(self.substore, clickapp.ClickList)

    def makeVisit(self, url='http://some.where', title='Some Where', indexIt=True):
        rootUrl = str(URL.fromString(url).click('/'))
        for domain in self.substore.query(Domain, Domain.url==rootUrl):
            domainCount = domain.visitCount
            break
        else:
            domainCount = 0

        (seenURL, visitCount, prevTimestamp) = (False, 0, None)
        for visit in self.substore.query(Visit, Visit.url==url):
            (seenURL, visitCount, prevTimestamp) = (True, visit.visitCount, visit.timestamp)
            break

        preClicks = self.recorder.visitCount

        self.recorder.recordClick(dict(url=url, title=title),
                                  indexIt=indexIt,storeFavicon=False)

        if not seenURL:
            self.assertEqual(self.recorder.visitCount, preClicks+1)

        visit = self.substore.findFirst(Visit, url=url)
        self.assertEqual(visit.visitCount, visitCount+1)

        if seenURL:
            self.assertEqual(self.substore.count(Visit, Visit.url==url), 1)
            self.failUnless(prevTimestamp < visit.timestamp)
        else:
            self.assertEqual(visit.title, title)

        self.assertEqual(visit.domain.visitCount, domainCount+1)
        self.assertEqual(visit.domain.url, rootUrl)

        return visit

    def assertNItems(self, store, item, count):
        self.assertEqual(self.itemCount(store, item), count)

    def assertUniform(self, *sequences):
        if 0 < len(sequences):
            first = sorted(sequences[0])
            for other in sequences[1:]:
                self.assertEqual(first, sorted(other))

    def randURL(self):
        return mktemp(dir='http://') + '.com/'

    def ignore(self, visit):
        self.recorder.ignoreVisit(visit)

    def record(self, title, url, **k):
        self.recorder.recordClick(dict(url=url, title=title, **k),
                                       indexIt=False, storeFavicon=False)
        
        return self.substore.findFirst(Visit, url=url)

    def urlsWithSameDomain(self, count=10):
        base = URL.fromString(self.randURL())
        yield str(base)
        for i in xrange(count-1):
            yield str(base.child(str(i)))

    def visitURLs(self, urls, indexIt=True):
        for (resname, url) in urls.iteritems():
            self.recorder.recordClick(dict(url=url, title=resname), indexIt=indexIt,
                                                    storeFavicon=False)

        cacheMan = iclickchronicle.ICache(self.substore)
        return cacheMan.tasks.notifyOnQuiescence()



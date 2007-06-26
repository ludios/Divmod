
from zope.interface import implements

from twisted.trial.unittest import TestCase

from axiom.store import Store
from axiom.item import Item
from axiom.attributes import integer
from axiom.substore import SubStore
from axiom.dependency import installOn

from nevow.athena import LiveFragment
from nevow import rend
from nevow.rend import WovenContext
from nevow.testutil import FakeRequest
from nevow.inevow import IRequest, IResource

from xmantissa.ixmantissa import ITemplateNameResolver
from xmantissa import website, webapp
from xmantissa.webtheme import getAllThemes


class FakeResourceItem(Item):
    unused = integer()
    implements(IResource)

class WebIDLocationTest(TestCase):

    def setUp(self):
        store = Store(self.mktemp())
        ss = SubStore.createNew(store, ['test']).open()
        self.pa = webapp.PrivateApplication(store=ss)
        installOn(self.pa, ss)


    def test_powersUpTemplateNameResolver(self):
        """
        L{PrivateApplication} implements L{ITemplateNameResolver} and should
        power up the store it is installed on for that interface.
        """
        self.assertIn(
            self.pa,
            self.pa.store.powerupsFor(ITemplateNameResolver))


    def test_suchWebID(self):
        """
        Verify that retrieving a webID gives the correct resource.
        """
        i = FakeResourceItem(store=self.pa.store)
        wid = self.pa.toWebID(i)
        ctx = FakeRequest()
        self.assertEqual(self.pa.createResource().locateChild(ctx, [wid]),
                         (i, []))


    def test_noSuchWebID(self):
        """
        Verify that non-existent private URLs generate 'not found' responses.
        """
        ctx = FakeRequest()
        for segments in [
            # something that looks like a valid webID
            ['0000000000000000'],
            # something that doesn't
            ["nothing-here"],
            # more than one segment
            ["two", "segments"]]:
            self.assertEqual(self.pa.createResource().locateChild(ctx, segments),
                             rend.NotFound)


class TestFragment(LiveFragment):
    def locateChild(self, ctx, segs):
        if segs[0] == 'child-of-fragment':
            return ('I AM A CHILD OF THE FRAGMENT', segs[1:])
        return rend.NotFound



class FragmentWrappingTestCase(TestCase):
    def test_childLookup(self):
        s = Store(self.mktemp())
        installOn(website.WebSite(store=s), s)
        s.parent = s

        ss = SubStore.createNew(s, ['child', 'lookup'])
        ss = ss.open()

        privapp = webapp.PrivateApplication(store=ss)
        installOn(privapp, ss)

        class factory:
            def getClient(self, seg):
                if seg == 'client-of-livepage':
                    return 'I AM A CLIENT OF THE LIVEPAGE'

        navpage = webapp.GenericNavigationAthenaPage(
                        privapp,
                        TestFragment(),
                        privapp.getPageComponents())

        navpage.factory = factory()

        self.assertEqual(navpage.locateChild(None, ('child-of-fragment',)),
                         ('I AM A CHILD OF THE FRAGMENT', ()))
        self.assertEqual(navpage.locateChild(None, ('client-of-livepage',)),
                         ('I AM A CLIENT OF THE LIVEPAGE', ()))



class AthenaNavigationTestCase(TestCase):
    """
    Test aspects of L{GenericNavigationAthenaPage}.
    """
    def _render(self, resource):
        """
        Test helper which tries to render the given resource.
        """
        ctx = WovenContext()
        req = FakeRequest()
        ctx.remember(req, IRequest)
        return req, resource.renderHTTP(ctx)


    def test_jsmodules(self):
        """
        Test that the C{jsmodule} child of a L{webapp.PrivateRootPage} is an
        object which will serve up JavaScript modules.
        """
        s = Store()
        s.parent = s
        a = webapp.PrivateApplication(store=s)
        installOn(a, s)
        p = webapp.PrivateRootPage(a, a.getPageComponents())
        resource, segments = p.locateChild(None, ('jsmodule',))
        self.failUnless(isinstance(resource, webapp.HashedJSModuleNames))
        self.assertEquals(segments, ())


    def test_resourceFactory(self):
        """
        Test that L{HashedJSModuleNames.resourceFactory} returns a
        L{static.Data} with the right C{expires} value.
        """
        f = self.mktemp()
        fObj = file(f, 'w')
        fObj.write('/* Hello, world. /*\n')
        fObj.close()
        m = webapp.HashedJSModuleNames({'module': f})
        d = m.resourceFactory(f)
        d.time = lambda: 12345
        req, result = self._render(d)
        self.assertEquals(
            req.headers['expires'],
            'Tue, 31 Dec 1974 03:25:45 GMT')
        self.assertEquals(
            result,
            '/* Hello, world. /*\n')



class _TestNavMixin(webapp.NavMixin):
    """
    L{webapp.NavMixin} subclass instrumented for test purposes.
    """
    called = False

    def getAllThemes(self):
        self.called = True
        return super(_TestNavMixin, self).getAllThemes()



class NavMixinTestCase(TestCase):
    """
    Test aspects of L{webapp.NavMixin}.
    """
    def setUp(self):
        s = Store()
        s.parent = s
        self.privateApp = webapp.PrivateApplication(store=s)
        installOn(self.privateApp, s)
        self.navMixin = _TestNavMixin(self.privateApp, self.privateApp.getPageComponents())


    def test_themeCache(self):
        """
        Test that NavMixin caches themes correctly.
        """
        self.assertEqual(self.navMixin.getAllThemes(), getAllThemes())


    def test_privateAppUsesCache(self):
        """
        Test that PrivateApplication can use a theme cache, but also works
        without one.
        """
        self.assertNotEqual(self.privateApp.getDocFactory('shell'), None)
        self.assertNotEqual(self.privateApp.getDocFactory('shell', _themeCache=self.navMixin), None)


    def test_navMixinUsesCache(self):
        """
        Test that the theme cache is actually used when calling
        L{NavMixin.getDocFactory}.
        """
        self.navMixin.getDocFactory('shell')
        self.assertEqual(self.navMixin.called, True)

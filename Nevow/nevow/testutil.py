# Copyright (c) 2004 Divmod.
# See LICENSE for details.


from zope.interface import implements

import twisted.python.components as tpc
from twisted.internet import defer

from formless import iformless
from nevow import inevow, context, athena, loaders, tags

class FakeChannel:
    def __init__(self, site):
        self.site = site


class FakeSite:
    pass


class FakeSession(tpc.Componentized):
    implements(inevow.ISession)
    def __init__(self, avatar):
        tpc.Componentized.__init__(self)
        self.avatar = avatar
        self.uid = 12345
    def getLoggedInRoot(self):
        return self.avatar


fs = FakeSession(None)


class FakeRequest(tpc.Componentized):
    implements(inevow.IRequest)
    args = {}
    failure = None
    context = None
    redirected_to = None

    method = 'GET'

    def __init__(self, headers=None, args=None, avatar=None, uri='/', currentSegments=None):
        """Create a FakeRequest instance.

        headers:
            dict of headers
        args:
            dict of args
        avatar:
            avatar to pass to the FakeSession instance
        uri:
            request URI
        currentSegments:
            list of segments that have "already been located"
        """
        tpc.Componentized.__init__(self)
        self.uri = uri
        self.prepath = []
        postpath = uri.split('?')[0]
        assert postpath.startswith('/')
        self.postpath = postpath[1:].split('/')
        if currentSegments is not None:
            for seg in currentSegments:
                assert seg == self.postpath[0]
                self.prepath.append(self.postpath.pop(0))
        self.headers = headers or {}
        self.args = args or {}
        self.sess = FakeSession(avatar)
        self.site = FakeSite()
        self.received_headers = {}

    def URLPath(self):
        from nevow import url
        return url.URL.fromString('')

    def getSession(self):
        return self.sess

    v = ''
    def write(self, x):
        self.v += x

    finished=False
    def finish(self):
        self.finished = True

    def getHeader(self, key):
        d = {
            'referer': '/',
            }
        return d.get(key)

    def setHeader(self, key, val):
        self.headers[key] = val

    def redirect(self, url):
        self.redirected_to = url

    def getRootURL(self):
        return ''

    def processingFailed(self, f):
        self.failure = f

    def setResponseCode(self, code):
        self.code = code

    def prePathURL(self):
        return 'http://localhost/%s'%'/'.join(self.prepath)

    def getClientIP(self):
        return '127.0.0.1'


try:
    from twisted.trial import unittest
    FailTest = unittest.FailTest
except:
    import unittest
    class FailTest(Exception): pass


import sys
class TestCase(unittest.TestCase):
    hasBools = (sys.version_info >= (2,3))
    _assertions = 0

    # This should be migrated to Twisted.
    def failUnlessSubstring(self, containee, container, msg=None):
        self._assertions += 1
        if container.find(containee) == -1:
            raise unittest.FailTest, (msg or "%r not in %r" % (containee, container))
    def failIfSubstring(self, containee, container, msg=None):
        self._assertions += 1
        if container.find(containee) != -1:
            raise unittest.FailTest, (msg or "%r in %r" % (containee, container))
    
    assertSubstring = failUnlessSubstring
    assertNotSubstring = failIfSubstring

    def assertNotIdentical(self, first, second, msg=None):
        self._assertions += 1
        if first is second:
            raise FailTest, (msg or '%r is %r' % (first, second))

    def failIfIn(self, containee, container, msg=None):
        self._assertions += 1
        if containee in container:
            raise FailTest, (msg or "%r in %r" % (containee, container))

    def assertApproximates(self, first, second, tolerance, msg=None):
        self._assertions += 1
        if abs(first - second) > tolerance:
            raise FailTest, (msg or "%s ~== %s" % (first, second))


if not hasattr(TestCase, 'mktemp'):
    def mktemp(self):
        import tempfile
        return tempfile.mktemp()
    TestCase.mktemp = mktemp


class AccumulatingFakeRequest(FakeRequest):
    """
    I am a fake IRequest that stores data written out in an instance variable.
    I also have a stub implementation of IFormDefaults.

    @ivar accumulator: The accumulated data from write().
    """
    implements(iformless.IFormDefaults)
    method = 'GET'
    def __init__(self):
        FakeRequest.__init__(self, uri='/', currentSegments=[''])
        self.d = defer.Deferred()
        self.accumulator = ''

    def write(self, data):
        FakeRequest.write(self, data)
        self.accumulator+=data

    def getDefault(self, key, context):
        return ''

    def remember(self, object, interface):
        pass


class FragmentWrapper(athena.LivePage):
    """
    I wrap myself around an Athena fragment, providing a minimal amount of html
    scaffolding in addition to an L{athena.LivePage}.
    """
    docFactory = loaders.stan(
                    tags.html[
                        tags.body[
                            tags.directive('fragment')]])

    def __init__(self, f):
        super(FragmentWrapper, self).__init__()
        self.f = f

    def render_fragment(self, ctx, data):
        self.f.setFragmentParent(self)
        return self.f


def renderLivePage(res, topLevelContext=context.WebContext):
    """
    Render the given LivePage resource, performing LivePage-specific cleanup.
    Return a Deferred which fires when it has rendered.
    """
    D = renderPage(res, topLevelContext)
    return D.addCallback(lambda x: (res._messageDeliverer.close(), x)[1])


def renderPage(res, topLevelContext=context.WebContext):
    """
    Render the given resource.  Return a Deferred which fires when it has
    rendered.
    """
    req = AccumulatingFakeRequest()
    return res.renderHTTP(
                topLevelContext(
                    tag=res, parent=context.RequestContext(tag=req))).addCallback(
                        lambda x: req.accumulator)

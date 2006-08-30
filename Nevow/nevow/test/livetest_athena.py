from twisted.internet import defer

from nevow import loaders, tags, athena
from nevow.athena import expose
from nevow.livetrial import testcase
from nevow.test import test_json

class WidgetInitializerArguments(testcase.TestCase):
    """
    Test that the arguments represented by the list returned by
    getInitialArguments are properly passed to the widget class's __init__
    method.
    """
    jsClass = u'Nevow.Athena.Tests.WidgetInitializerArguments'

    _args = [1, u"two", [3.0 for four in range(5)]]

    def getInitialArguments(self):
        return self._args

    def test(self, args):
        self.assertEquals(self._args, args)
    expose(test)


class ClientToServerArgumentSerialization(testcase.TestCase):
    """
    Tests that arguments passed to a method on the server are properly
    received.
    """

    jsClass = u'Nevow.Athena.Tests.ClientToServerArgumentSerialization'

    def test(self, i, f, s, l, d):
        self.assertEquals(i, 1)
        self.assertEquals(f, 1.5)
        self.failUnless(isinstance(s, unicode))
        self.assertEquals(s, u'Hello world')
        self.failUnless(isinstance(l[2], unicode))
        self.assertEquals(l, [1, 1.5, u'Hello world'])
        self.assertEquals(d, {u'hello world': u'object value'})
        self.failUnless(isinstance(d.keys()[0], unicode))
        self.failUnless(isinstance(d.values()[0], unicode))
    expose(test)


class ClientToServerResultSerialization(testcase.TestCase):
    """
    Tests that the return value from a method on the server is properly
    received by the client.
    """

    jsClass = u'Nevow.Athena.Tests.ClientToServerResultSerialization'

    def test(self, i, f, s, l, d):
        return (i, f, s, l, d)
    expose(test)

class JSONRoundtrip(testcase.TestCase):
    """
    Test that all test cases from nevow.test.test_json roundtrip correctly
    through the real client implementation, too.
    """

    jsClass = u'Nevow.Athena.Tests.JSONRoundtrip'

    def test(self):
        cases = test_json.TEST_OBJECTS + test_json.TEST_STRINGLIKE_OBJECTS
        def _verifyRoundtrip(_cases):
            for v1, v2 in zip(cases, _cases):
                self.assertEquals(v1, v2)
        return self.callRemote('identity', cases).addCallback(_verifyRoundtrip)
    expose(test)



class ExceptionFromServer(testcase.TestCase):
    """
    Tests that when a method on the server raises an exception, the client
    properly receives an error.
    """

    jsClass = u'Nevow.Athena.Tests.ExceptionFromServer'

    def testSync(self, s):
        raise Exception(s)
    expose(testSync)



class AsyncExceptionFromServer(testcase.TestCase):
    """
    Tests that when a method on the server raises an exception asynchronously,
    the client properly receives an error.
    """

    jsClass = u'Nevow.Athena.Tests.AsyncExceptionFromServer'

    def testAsync(self, s):
        return defer.fail(Exception(s))
    expose(testAsync)



class ExceptionFromClient(testcase.TestCase):
    """
    Tests that when a method on the client raises an exception, the server
    properly receives an error.
    """

    jsClass = u'Nevow.Athena.Tests.ExceptionFromClient'

    def loopbackError(self):
        return self.callRemote('generateError').addErrback(self.checkError)
    expose(loopbackError)


    def checkError(self, f):
        f.trap(athena.JSException)
        if u'This is a test exception' in f.value.args[0]:
            return True
        else:
            raise f



class AsyncExceptionFromClient(testcase.TestCase):
    """
    Tests that when a method on the client raises an exception asynchronously,
    the server properly receives an error.
    """

    jsClass = u'Nevow.Athena.Tests.AsyncExceptionFromClient'

    def loopbackError(self):
        return self.callRemote('generateError').addErrback(self.checkError)
    expose(loopbackError)


    def checkError(self, f):
        f.trap(athena.JSException)
        if u'This is a deferred test exception' in f.value.args[0]:
            return True
        else:
            raise f

class ServerToClientArgumentSerialization(testcase.TestCase):
    """
    Tests that a method invoked on the client by the server is passed the
    correct arguments.
    """

    jsClass = u'Nevow.Athena.Tests.ServerToClientArgumentSerialization'

    def test(self):
        return self.callRemote('reverse', 1, 1.5, u'hello', {u'world': u'value'});
    expose(test)



class ServerToClientResultSerialization(testcase.TestCase):
    """
    Tests that the result returned by a method invoked on the client by the
    server is correct.
    """

    jsClass = u'Nevow.Athena.Tests.ServerToClientResultSerialization'

    def test(self):
        def cbResults(result):
            self.assertEquals(result[0], 1)
            self.assertEquals(result[1], 1.5)
            self.assertEquals(result[2], u'hello')
            self.assertEquals(result[3], {u'world': u'value'})
        d = self.callRemote('reverse')
        d.addCallback(cbResults)
        return d
    expose(test)



class WidgetInATable(testcase.TestCase):
    jsClass = u"Nevow.Athena.Tests.WidgetInATable"

    def getTestContainer(self):
        return tags.table[tags.tbody[tags.tr[tags.td[tags.slot('widget')]]]]



class WidgetIsATable(testcase.TestCase):
    jsClass = u"Nevow.Athena.Tests.WidgetIsATable"

    def getWidgetTag(self):
        """
        Make this widget's top-level node a table node.
        """
        return tags.table


    def getWidgetDocument(self):
        """
        Create a body for the table node at the top of this widget.  Put a row
        and a column in it.
        """
        return tags.tbody[tags.tr[tags.td]]



class ParentChildRelationshipTest(testcase.TestCase):
    jsClass = u"Nevow.Athena.Tests.ChildParentRelationshipTest"

    def getWidgetDocument(self):
        """
        Return a tag which will have numerous children rendered beneath it.
        """
        return tags.div(render=tags.directive('childrenWidgets'))


    def render_childrenWidgets(self, ctx, data):
        """
        Put some children into this widget.  The client portion of this test
        will assert things about their presence in C{Widget.childWidgets}.
        """
        for i in xrange(3):
            yield ChildFragment(self.page, i)


    def getChildCount(self):
        return 3
    expose(getChildCount)



class ChildFragment(athena.LiveFragment):
    jsClass = u'Nevow.Athena.Tests.ChildParentRelationshipTest'

    docFactory = loaders.stan(tags.div(render=tags.directive('liveFragment'))[
        tags.div(render=tags.directive('childrenWidgets')),
        'child'])

    def __init__(self, page, childCount):
        super(ChildFragment, self).__init__()
        self.page = page
        self.childCount = childCount


    def render_childrenWidgets(self, ctx, data):
        # yield tags.div['There are ', self.childCount, 'children']
        for i in xrange(self.childCount):
            yield ChildFragment(self.page, self.childCount - 1)


    def getChildCount(self):
        return self.childCount
    expose(getChildCount)



class AutomaticClass(testcase.TestCase):
    jsClass = u'Nevow.Athena.Tests.AutomaticClass'
    docFactory = loaders.stan(tags.div(render=tags.directive('liveTest')))



class AthenaHandler(testcase.TestCase):
    jsClass = u'Nevow.Athena.Tests.AthenaHandler'

    def getWidgetDocument(self):
        """
        Return a button with an automatic athena handler attached to its
        onclick event.
        """
        return tags.button[
            '<athena:handler>',
            athena.handler(event='onclick', handler='handler')]



class FirstNodeByAttribute(testcase.TestCase):
    jsClass = u'Nevow.Athena.Tests.FirstNodeByAttribute'
    docFactory = loaders.stan(tags.div(render=tags.directive('liveTest')))



class DynamicWidgetInstantiation(testcase.TestCase):
    jsClass = u'Nevow.Athena.Tests.DynamicWidgetInstantiation'

    def getWidgets(self):
        widgets = []
        f = athena.LiveFragment(docFactory=loaders.stan(tags.div[widgets]))
        f.setFragmentParent(self)
        for i in xrange(5):
            widgets.append(athena.LiveFragment(docFactory=loaders.stan(tags.span(render=tags.directive('liveFragment')))))
            widgets[-1].setFragmentParent(f)
        return f
    athena.expose(getWidgets)



class GettingWidgetlessNodeRaisesException(testcase.TestCase):
    jsClass = u'Nevow.Athena.Tests.GettingWidgetlessNodeRaisesException'



class RemoteMethodErrorShowsDialog(testcase.TestCase):
    jsClass = u'Nevow.Athena.Tests.RemoteMethodErrorShowsDialog'

    def raiseValueError(self):
        raise ValueError('hi')
    athena.expose(raiseValueError)

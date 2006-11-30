
from twisted.trial import unittest
from twisted.internet import defer
from twisted.application import service

from axiom import store, item, attributes, scheduler
from axiom.dependency import installOn

from clickchronicle import queue

class TestTask(item.Item):
    typeName = 'test_task'
    schemaVersion = 1

    taskSpecificInformation = attributes.text(default=u'never run')

    def do(self):
        self.taskSpecificInformation = u'ran'

class QueueTestCase(unittest.TestCase):
    def setUp(self):
        self.store = store.Store()

        self.queue = queue.Queue(store=self.store)
        installOn(self.queue, self.store)

        service.IService(self.store).startService()

    def tearDown(self):
        service.IService(self.store).stopService()


    def testLength(self):
        self.assertEquals(len(self.queue), 0)

        for i in range(3):
            self.queue.addTask(TestTask(store=self.store))
            self.assertEquals(len(self.queue), i + 1)

        def cbRan(ignored):
            self.assertEquals(len(self.queue), 0)

        return self.queue.notifyOnQuiescence().addCallback(cbRan)


    def testImmediateQuiescenceNotification(self):
        # The queue has no tasks - the Deferred given back should fire
        # with no more work on anyone's part.
        return defer.DeferredList([
                self.queue.notifyOnQuiescence(),
                self.queue.notifyOnQuiescence()])


    def testDelayedQuiescenceNotification(self):
        t = TestTask(store=self.store)
        self.queue.addTask(t)

        def cbQuiet(ignored):
            self.assertEquals(t.taskSpecificInformation, u'ran')

        return self.queue.notifyOnQuiescence().addCallback(cbQuiet)

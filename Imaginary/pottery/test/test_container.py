# -*- test-case-name: pottery.test -*-

from twisted.trial import unittest

from axiom import store

from pottery import epottery, ipottery, objects

class ContainerTestCase(unittest.TestCase):
    def setUp(self):
        self.store = store.Store()
        self.containmentCore = objects.Object(store=self.store, name=u"container")
        self.container = objects.Container(store=self.store, capacity=1)
        self.container.installOn(self.containmentCore)
        self.object = objects.Object(store=self.store, name=u"object")


    def testAdd(self):
        """
        Test that successfully adding an object to a container properly adjusts
        the world graph - in particular, the contents list of the container and
        the location of the object.
        """
        self.container.add(self.object)
        self.assertEquals(list(self.container.getContents()), [self.object])
        self.assertIdentical(self.object.location, self.containmentCore)


    def testRemove(self):
        """
        Test that successfully removing an object from a container properly
        adjusts the world graph - in particular, the contents list of the
        container and the location of the object.
        """
        self.testAdd()
        self.container.remove(self.object)
        self.assertEquals(list(self.container.getContents()), [])
        self.assertIdentical(self.object.location, None)


    def testOverflowing(self):
        """
        Test the capacity feature of the container implementation as it
        interacts with the weight feature of the object implementation.
        """
        self.container.capacity = 1
        self.object.weight = 2
        self.assertRaises(epottery.DoesntFit, self.container.add, self.object)
        self.assertEquals(list(self.container.getContents()), [])
        self.assertIdentical(self.object.location, None)


    def testClosed(self):
        """
        Test the closed feature of the container implementation.
        """
        self.container.closed = True
        self.assertRaises(epottery.Closed, self.container.add, self.object)
        self.assertEquals(list(self.container.getContents()), [])
        self.assertIdentical(self.object.location, None)

        self.container.closed = False
        self.container.add(self.object)
        self.container.closed = True

        self.assertRaises(epottery.Closed, self.container.remove, self.object)
        self.assertEquals(list(self.container.getContents()), [self.object])
        self.assertIdentical(self.object.location, self.containmentCore)

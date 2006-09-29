# -*- test-case-name: axiom.test.test_scheduler -*-


from datetime import timedelta

from twisted.trial import unittest
from twisted.trial.unittest import TestCase
from twisted.application.service import IService
from twisted.internet.defer import Deferred
from twisted.internet.task import Clock
from twisted.python import log

from epsilon.extime import Time

from axiom.scheduler import Scheduler, SubScheduler, TimedEvent, _SubSchedulerParentHook, TimedEventFailureLog
from axiom.store import Store
from axiom.item import Item
from axiom.substore import SubStore

from axiom.attributes import integer, text, inmemory, boolean, timestamp
from axiom.iaxiom import IScheduler


class TestEvent(Item):

    typeName = 'test_event'
    schemaVersion = 1

    deferred = inmemory()       # these won't fall out of memory due to
                                # caching, thanks.
    testCase = inmemory()

    name = text()

    maxRunCount = integer()     # fail the test if we run more than this many
                                # times
    runCount = integer()
    runAgain = integer()        # milliseconds to add, then run again
    winner = integer(default=0) # is this the event that is supposed to
                                # complete the test successfully?

    def __init__(self, **kw):
        self.deferred = None
        super(TestEvent, self).__init__(**kw)
        self.runCount = 0

    def run(self):
        # When this is run from testSubScheduler, we want to make an
        # additional assertion.  There is exactly one SubStore in this
        # configuration, so there should be no more than one
        # TimedEvent with a _SubSchedulerParentHook as its runnable.
        if self.store.parent is not None:
            count = 0
            s = self.store.parent
            for evt in s.query(TimedEvent):
                if isinstance(evt.runnable, _SubSchedulerParentHook):
                    count += 1
            if count > 1:
                return self.fail("Too many TimedEvents for the SubStore", count)

        self.runCount += 1
        if self.runCount > self.maxRunCount:
            return self.fail("%s ran too many times"% (self.name))
        if self.runAgain is not None:
            result = Time() + timedelta(milliseconds=self.runAgain)
            self.runAgain = None
        else:
            if self.winner and self.deferred is not None:
                self.deferred.callback('done')
            result = None
        return result

    def fail(self, *msg):
        self.deferred.errback(self.testCase.failureException(*msg))


class NotActuallyRunnable(Item):
    huhWhat = integer()

class SpecialError(Exception):
    pass

class SpecialErrorHandler(Item):
    huhWhat = integer()
    broken = integer(default=0)
    procd = integer(default=0)

    def run(self):
        self.broken = 1
        raise SpecialError()

    def timedEventErrorHandler(self, timedEvent, failureObj):
        failureObj.trap(SpecialError)
        self.procd = 1

class SchedTest(unittest.TestCase):

    def setUp(self):
        # self.storePath = self.mktemp()
        self.store = Store()
        Scheduler(store=self.store).installOn(self.store)
        IService(self.store).startService()

    def tearDown(self):
        IService(self.store).stopService()

    def _doTestScheduler(self, s):
        # create 3 timed events.  the first one fires.  the second one fires,
        # then reschedules itself.  the third one should never fire because the
        # reactor is shut down first.  assert that the first and second fire
        # only once, and that the third never fires.

        d = Deferred()

        interval = 30

        t1 = TestEvent(testCase=self,
                       name=u't1',
                       store=s, maxRunCount=1, runAgain=None, deferred=d)
        t2 = TestEvent(testCase=self,
                       name=u't2',
                       store=s, maxRunCount=2, runAgain=interval, deferred=d, winner=True)
        t3 = TestEvent(testCase=self,
                       name=u't3',
                       store=s, maxRunCount=0, runAgain=None, deferred=d)

        now = Time()
        self.ts = [t1, t2, t3]

        S = IScheduler(s)

        # Schedule them out of order to make sure behavior doesn't
        # depend on tasks arriving in soonest-to-latest order.
        S.schedule(t2, now + timedelta(milliseconds=interval * 2))
        S.schedule(t1, now + timedelta(milliseconds=interval * 1))
        S.schedule(t3, now + timedelta(milliseconds=interval * 100))

        return d


    def testUnscheduling(self):
        """
        Test the unscheduleFirst method of the scheduler.
        """
        now = Time()
        d = Deferred()
        sch = IScheduler(self.store)
        t1 = TestEvent(testCase=self, name=u't1', store=self.store, maxRunCount=0)
        t2 = TestEvent(testCase=self, name=u't2', store=self.store, maxRunCount=1, runAgain=None, winner=True, deferred=d)

        # Make sure the inmemory attributes hang around
        self.ts = [t1, t2]

        sch.schedule(t1, now + timedelta(milliseconds=100))
        sch.schedule(t2, now + timedelta(milliseconds=200))
        sch.unscheduleFirst(t1)

        return d


    def test_inspection(self):
        """
        Test that the L{scheduledTimes} method returns an iterable of all the
        times at which a particular item is scheduled to run.
        """
        now = Time()
        off = timedelta(seconds=3)
        sch = IScheduler(self.store)
        runnable = TestEvent(store=self.store)
        sch.schedule(runnable, now)
        sch.schedule(runnable, now + off)
        sch.schedule(runnable, now + off + off)

        self.assertEquals(
            list(sch.scheduledTimes(runnable)),
            [now, now + off, now + off + off])



class TopStoreSchedTest(SchedTest):

    def testBasicScheduledError(self):
        S = IScheduler(self.store)
        now = Time()
        S.schedule(NotActuallyRunnable(store=self.store), now)
        d = Deferred()
        te = TestEvent(store=self.store, testCase=self,
                       name=u't1', maxRunCount=1, runAgain=None,
                       winner=True, deferred=d)
        self.te = te            # don't gc the deferred
        now2 = Time()
        S.schedule(te, now2)
        self.assertEquals(
            self.store.query(TimedEventFailureLog).count(), 0)
        def later(result):
            errs = log.flushErrors(AttributeError)
            self.assertEquals(len(errs), 1)
            self.assertEquals(self.store.query(TimedEventFailureLog).count(), 1)
        return d.addCallback(later)

    def testScheduledErrorWithHandler(self):
        S = IScheduler(self.store)
        now = Time()
        spec = SpecialErrorHandler(store=self.store)
        S.schedule(spec, now)
        d = Deferred()
        te = TestEvent(store=self.store, testCase=self,
                       name=u't1', maxRunCount=1, runAgain=None,
                       winner=True, deferred=d)
        self.te = te            # don't gc the deferred
        now2 = Time()
        S.schedule(te, now2)
        self.assertEquals(
            self.store.query(TimedEventFailureLog).count(), 0)
        def later(result):
            errs = log.flushErrors(SpecialError)
            self.assertEquals(len(errs), 1)
            self.assertEquals(self.store.query(TimedEventFailureLog).count(), 0)
            self.failUnless(spec.procd)
            self.failIf(spec.broken)
        return d.addCallback(later)

    def testScheduler(self):
        self._doTestScheduler(self.store)

class SubSchedTest(SchedTest):
    def setUp(self):
        self.storePath = self.mktemp()
        self.store = Store(self.storePath)
        Scheduler(store=self.store).installOn(self.store)
        self.svc = IService(self.store)
        self.svc.startService()

    def tearDown(self):
        return self.svc.stopService()

    def testSubScheduler(self):
        substoreItem = SubStore.createNew(self.store, ['scheduler_test'])
        substore = substoreItem.open()
        SubScheduler(store=substore).installOn(substore)

        return self._doTestScheduler(substore)


class ServiceNotRunningMixin(unittest.TestCase):
    """
    A set of tests to verify that things *aren't* scheduled with the reactor
    when the scheduling service isn't running, merely persisted to the
    database.
    """

    def setUp(self):
        """
        Create a store with a scheduler installed on it and hook the C{now} and
        C{callLater} methods of that scheduler so their behavior can be
        controlled by these tests.
        """
        self.calls = []
        self.store = Store(self.mktemp())
        self.siteScheduler = Scheduler(store=self.store)
        self.siteScheduler.installOn(self.store)
        self.siteScheduler.callLater = self._callLater


    def _callLater(self, s, f, *a, **k):
        self.calls.append((s, f, a, k))


    def test_schedule(self):
        """
        Test that if an event is scheduled against a scheduler which is not
        running, not transient scheduling (eg, reactor.callLater) is performed.
        """
        return self._testSchedule(self.siteScheduler)


    def test_subSchedule(self):
        """
        The same as test_schedule, except using a subscheduler.
        """
        subst = SubStore.createNew(self.store, ['scheduler_test'])
        substore = subst.open()
        subscheduler = SubScheduler(store=substore)
        subscheduler.installOn(substore)
        return self._testSchedule(subscheduler)

    def test_orphanedSubSchedule(self):
        """
        The same as test_scheduler, except using a subscheduler that is orphaned.
        """
        subscheduler = SubScheduler(store=self.store)
        subscheduler.installOn(self.store)
        return self._testSchedule(subscheduler)


    def _testSchedule(self, scheduler):
        t1 = TestEvent(store=scheduler.store)
        scheduler.schedule(t1, Time.fromPOSIXTimestamp(0))
        self.failIf(self.calls,
                    "Should not have had any calls: %r" % (self.calls,))
        self.assertIdentical(
            scheduler._getNextEvent(Time.fromPOSIXTimestamp(1)).runnable, t1)



class ScheduleCallingItem(Item):
    """
    Item which invokes C{schedule} on its store's L{IScheduler} from its own
    C{run} method.
    """

    ran = boolean(default=False)
    rescheduleFor = timestamp()

    def run(self):
        scheduler = IScheduler(self.store)
        scheduler.schedule(self, self.rescheduleFor)
        self.ran = True



class NullRunnable(Item):
    """
    Runnable item which does nothing.
    """
    ran = boolean(default=False)

    def run(self):
        pass



class SubStoreSchedulerReentrancy(TestCase):
    """
    Test re-entrant scheduling calls on an item run by a SubScheduler.
    """
    def setUp(self):
        self.clock = Clock()

        self.dbdir = self.mktemp()
        self.store = Store(self.dbdir)
        self.substoreItem = SubStore.createNew(self.store, ['sub'])
        self.substore = self.substoreItem.open()

        Scheduler(store=self.store).installOn(self.store)
        SubScheduler(store=self.substore).installOn(self.substore)

        self.scheduler = IScheduler(self.store)
        self.subscheduler = IScheduler(self.substore)

        self.scheduler.callLater = self.clock.callLater
        self.scheduler.now = lambda: Time.fromPOSIXTimestamp(self.clock.seconds())
        self.subscheduler.now = lambda: Time.fromPOSIXTimestamp(self.clock.seconds())

        IService(self.store).startService()


    def tearDown(self):
        return IService(self.store).stopService()


    def _scheduleRunner(self, now, offset):
        scheduledAt = Time.fromPOSIXTimestamp(now + offset)
        rescheduleFor = Time.fromPOSIXTimestamp(now + offset + 10)
        runnable = ScheduleCallingItem(store=self.substore, rescheduleFor=rescheduleFor)
        self.subscheduler.schedule(runnable, scheduledAt)
        return runnable


    def testSchedule(self):
        """
        Test the schedule method, as invoked from the run method of an item
        being run by the subscheduler.
        """
        now = self.clock.seconds()
        runnable = self._scheduleRunner(now, 10)

        self.clock.advance(11)

        self.assertEqual(
            list(self.subscheduler.scheduledTimes(runnable)),
            [Time.fromPOSIXTimestamp(now + 20)])

        hook = self.store.findUnique(
            _SubSchedulerParentHook,
            _SubSchedulerParentHook.loginAccount == self.substoreItem)

        self.assertEqual(
            list(self.scheduler.scheduledTimes(hook)),
            [Time.fromPOSIXTimestamp(now + 20)])


    def testScheduleWithLaterTimedEvents(self):
        """
        Like L{testSchedule}, but use a SubScheduler which has pre-existing
        TimedEvents which are beyond the new runnable's scheduled time (to
        trigger the reschedule-using code-path in
        _SubSchedulerParentHook._schedule).
        """
        now = self.clock.seconds()
        when = Time.fromPOSIXTimestamp(now + 30)
        null = NullRunnable(store=self.substore)
        self.subscheduler.schedule(null, when)
        runnable = self._scheduleRunner(now, 10)

        self.clock.advance(11)

        self.assertEqual(
            list(self.subscheduler.scheduledTimes(runnable)),
            [Time.fromPOSIXTimestamp(now + 20)])

        self.assertEqual(
            list(self.subscheduler.scheduledTimes(null)),
            [Time.fromPOSIXTimestamp(now + 30)])

        hook = self.store.findUnique(
            _SubSchedulerParentHook,
            _SubSchedulerParentHook.loginAccount == self.substoreItem)

        self.assertEqual(
            list(self.scheduler.scheduledTimes(hook)),
            [Time.fromPOSIXTimestamp(20)])


    def testScheduleWithEarlierTimedEvents(self):
        """
        Like L{testSchedule}, but use a SubScheduler which has pre-existing
        TimedEvents which are before the new runnable's scheduled time.
        """
        now = self.clock.seconds()
        when = Time.fromPOSIXTimestamp(now + 15)
        null = NullRunnable(store=self.substore)
        self.subscheduler.schedule(null, when)
        runnable = self._scheduleRunner(now, 10)

        self.clock.advance(11)

        self.assertEqual(
            list(self.subscheduler.scheduledTimes(runnable)),
            [Time.fromPOSIXTimestamp(now + 20)])

        self.assertEqual(
            list(self.subscheduler.scheduledTimes(null)),
            [Time.fromPOSIXTimestamp(now + 15)])

        hook = self.store.findUnique(
            _SubSchedulerParentHook,
            _SubSchedulerParentHook.loginAccount == self.substoreItem)

        self.assertEqual(
            list(self.scheduler.scheduledTimes(hook)),
            [Time.fromPOSIXTimestamp(now + 15)])


    def testMultipleEventsPerTick(self):
        """
        Test running several runnables in a single tick of the subscheduler.
        """
        now = self.clock.seconds()
        runnables = [
            self._scheduleRunner(now, 10),
            self._scheduleRunner(now, 11),
            self._scheduleRunner(now, 12)]

        self.clock.advance(13)

        for n, runnable in enumerate(runnables):
            self.assertEqual(
                list(self.subscheduler.scheduledTimes(runnable)),
                [Time.fromPOSIXTimestamp(now + n + 20)])

        hook = self.store.findUnique(
            _SubSchedulerParentHook,
            _SubSchedulerParentHook.loginAccount == self.substoreItem)

        self.assertEqual(
            list(self.scheduler.scheduledTimes(hook)),
            [Time.fromPOSIXTimestamp(now + 20)])

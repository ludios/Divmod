# -*- test-case-name: clickchronicle.test.test_queue -*-

import datetime

from twisted.internet import defer
from twisted.python import log

from epsilon import extime

from axiom import iaxiom, item, attributes

class TaskError(Exception):
    """
    An error occurred while processing a particular task.  The task
    should be retried.  The error will not be logged.
    """

class _Task(item.Item):
    """
    @ivar task: A reference to an Item with a do method.  This item
    defines the actual behavior of this task.

    @ivar added: The time at which this task was added.

    @ivar retries: The number of times this task has been attempted so
    far.

    @ivar maxRetries: The maximum number of times this task will be
    attempted.

    @ivar lastAttempt: The time at which this task was most recently
    run.

    @ivar queue: The task queue which contains this task.
    """

    schemaVersion = 1
    typeName = 'clickchronicle_queued_task'

    task = attributes.reference()
    added = attributes.timestamp()
    retries = attributes.integer(default=0)
    maxRetries = attributes.integer()
    lastAttempt = attributes.timestamp()
    queue = attributes.reference()

    def do(self):
        return self.task.do()


class Queue(item.Item):
    """
    @ivar rate: The number of tasks which will be attempted at a time.

    @ivar interval: The number of milliseconds between the completion
    of one set of tasks and the initiation of the next set.

    @ivar maxRetries: The number of retryable failures which will be
    allowed before a task is abandoned.
    """

    schemaVersion = 1
    typeName = 'clickchronicle_queue'

    rate = attributes.integer(default=3)
    interval = attributes.integer(default=5000)
    maxRetries = attributes.integer(default=3)
    initialDelay = 250

    _waitingForQuiet = attributes.inmemory()

    def activate(self):
        self._waitingForQuiet = []

    def _keepMeInMemory(self, passthrough):
        return passthrough

    def notifyOnQuiecence(self):
        print 'Q len:',self.store.count(_Task, _Task.queue == self)
        if not self.store.count(_Task, _Task.queue == self):
            return defer.succeed(None)
        d = defer.Deferred()
        self._waitingForQuiet.append(d)
        d.addCallback(self._keepMeInMemory)
        return d

    def addTask(self, task, maxRetries=None):
        if maxRetries is None:
            maxRetries = self.maxRetries
        _Task(store=self.store,
              task=task,
              added=extime.Time(),
              lastAttempt=extime.Time(),
              maxRetries=maxRetries,
              queue=self)
        taskCount = self.store.count(_Task, _Task.queue == self)
        if taskCount <= 1:
            # if the only task is the one we just created, kick it off
            # with a smaller delay
            delay = self.initialDelay
        else:
            delay = self.interval
        self._reschedule(delay=delay)

    def _cbTask(self, ignored, task):
        task.deleteFromStore()

    def _ebTask(self, err, task):
        if not err.check(TaskError):
            log.msg("Error processing task: %r" % (task,))
            log.err(err)

        if task.retries > task.maxRetries or not task.task.retryableFailure(err):
            log.msg("Giving up on %r" % (task.task,))
            task.deleteFromStore()
        else:
            task.retries += 1
            task.lastAttempt = extime.Time()

    def _cbRun(self, ignored):
        if self.store.count(_Task, _Task.queue == self):
            self._reschedule()
        else:
            dl = self._waitingForQuiet
            self._waitingForQuiet = []
            for d in dl:
                d.callback(None)

    def _reschedule(self, delay=None):
        if delay is None:
            delay = self.interval
        sch = iaxiom.IScheduler(self.store)
        sch.schedule(
            self,
            extime.Time() + datetime.timedelta(milliseconds=delay))

    def run(self):
        dl = []
        for task in self.store.query(_Task,
                                     _Task.queue == self,
                                     sort=_Task.lastAttempt.ascending,
                                     limit=self.rate):
            dl.append(task.do().addCallbacks(self._cbTask, self._ebTask, callbackArgs=(task,), errbackArgs=(task,)))
        defer.DeferredList(dl).addCallback(self._cbRun)

# Copyright (c) 2005 Divmod Inc. See LICENSE file for details.

from twisted.trial import unittest

import xapwrap.index, tempfile, shutil, os, time, signal
from xapwrap.document import Document, TextField, SortKey, Keyword, Value

# TODO - Make these test work with flint backend
# Manipulating and checking the 'meta' file is quartz-specific
# All the files in the directory have changed names betweem quartz and flint

class ExceptionTranslatorTests(unittest.TestCase):
    def setUp(self):
        self.dbDir = tempfile.mkdtemp()
        x = xapwrap.index.ExceptionTranslater.openIndex(
            False, self.dbDir, xapwrap.index.xapian.DB_CREATE)
        x.flush()

    def xtearDown(self):
        shutil.rmtree(self.dbDir)

    def testOpeningError(self):
        os.remove(os.path.join(self.dbDir, 'meta'))
        self.assertRaises(xapwrap.index.DatabaseOpeningError,
                       xapwrap.index.ExceptionTranslater.openIndex,
                       True, self.dbDir)

    def testCorruptionError(self):
        f = file(os.path.join(self.dbDir, 'meta'), 'w')
        f.write('1234567890'*100)
        f.close()
        self.assertRaises(xapwrap.index.DatabaseCorruptionError,
                       xapwrap.index.ExceptionTranslater.openIndex,
                       True, self.dbDir)

    def testLockError(self):
        x = xapwrap.index.ExceptionTranslater.openIndex(
            False, self.dbDir, xapwrap.index.xapian.DB_OPEN)
        self.assertRaises(xapwrap.index.DatabaseLockError,
                       xapwrap.index.ExceptionTranslater.openIndex,
                       False, self.dbDir, xapwrap.index.xapian.DB_OPEN)

    def test_docNotFoundError(self):
        idx = xapwrap.index.ExceptionTranslater.openIndex(True, self.dbDir)
        self.assertRaises(xapwrap.index.DocNotFoundError, idx.get_document, 1)

    def test_invalidArgError(self):
        idx = xapwrap.index.ExceptionTranslater.openIndex(True, self.dbDir)
        self.assertRaises(xapwrap.index.InvalidArgumentError, idx.get_document, 0)


doc = Document(uid = 45, textFields = TextField('text', 'hi there'))


class SimpleXapianHarness:
    def setup_method(self, method):
        self.indexPaths = []

    def mktemp(self):
        path = tempfile.mktemp()
        self.indexPaths.append(path)
        return path

    def teardown_method(self, method):
        for path in self.indexPaths:
            shutil.rmtree(path, True)

class TestLocks(unittest.TestCase, SimpleXapianHarness):
    def checkLockFiles(self, path):
        xapLockFile = os.path.join(path, xapwrap.index.XAPIAN_LOCK_FILENAME)
        myLockFile = os.path.join(path, xapwrap.index.XAPWRAP_LOCK_FILENAME)
        return os.path.exists(xapLockFile) and os.path.islink(myLockFile)

    def test_GoodLocking(self):
        # open a xapian index and close it and verify that we can open
        # the index again from this process
        path = self.mktemp()
        idx = xapwrap.index.Index(path, True)
        idx.index(doc)
        idx.flush()
        assert self.checkLockFiles(path)

        idx.close()
        assert not(self.checkLockFiles(path))

        idx = xapwrap.index.Index(path, False)
        idx.close()

    def test_BadLocking(self):
        # open a xapian index twice and verify that the second open
        # attempt fails, even in process
        path = self.mktemp()
        idx = xapwrap.index.Index(path, True)
        idx.index(doc)
        idx.flush()
        assert self.checkLockFiles(path)

        idx2 = xapwrap.index.Index(path, False)
        self.assertRaises(xapwrap.index.DatabaseLockError, idx2.index, doc)

    def test_AfterMurder(self):
        # open a xapian index in another process, flush some data to the
        # index, and kill the process. verify that we can open the index
        # from this process
        path = self.mktemp()
        childPid = os.fork()
        if childPid == 0:
            # i must be the child!
            idx = xapwrap.index.Index(path, True)
            idx.index(doc)
            idx.flush()
            os._exit(0)
        else:
            # i must be the parent!
            os.waitpid(childPid, 0)
            assert self.checkLockFiles(path)
            idx2 = xapwrap.index.Index(path, True)
            idx2.index(doc)
            idx2.close()

    def test_AfterLiveProcess(self):
        # open a xapian index in another process and keep the process
        # alive while we verify that we cannot open the index from this
        # process
        path = self.mktemp()
        childPid = os.fork()
        if childPid == 0:
            # i must be the child!
            idx = xapwrap.index.Index(path, True)
            idx.index(doc)
            idx.flush()
            # sleep forever
            time.sleep(1000)
        else:
            # i must be the parent!

            # i should wait for the child to do its thing, then try to
            # open an index in the same place and verify that i fail,
            # and then kill the child and wait for it to die

            DELAY = 0.01 # 10 ms
            MAX_DELAY = 2

            try:
                startTime = time.time()
                childReadyYet = False
                currentDelay = 0
                while not(childReadyYet) and (currentDelay < MAX_DELAY):
                    time.sleep(DELAY)
                    childReadyYet = self.checkLockFiles(path)
                    currentDelay = time.time() - startTime
                if not(childReadyYet):
                    os.kill(childPid, signal.SIGKILL)
                    assert False, "Child process failed to write xapian index before running out of time."
                idx2 = xapwrap.index.Index(path, True)
                self.assertRaises(xapwrap.index.DatabaseLockError, idx2.index, doc)
            finally:
                os.kill(childPid, signal.SIGKILL)
                os.waitpid(childPid, 0)

class TestSmartness(unittest.TestCase, SimpleXapianHarness):
    def test_CatchUID1(self):
        path = self.mktemp()
        s = xapwrap.index.SmartIndex(path, True)
        self.assertRaises(xapwrap.index.InvalidArgumentError,
                       s.index, Document(uid = 1))

    def test_SmartIndex(self):
        path = self.mktemp()
        doc = Document(uid = 2, textFields = TextField('text', 'yo yo yo'),
                               sortFields = SortKey('hi', 'there'),
                               keywords = Keyword('boo', 'yah'))
        s = xapwrap.index.SmartIndex(path, True)
        s.index(doc)
        s.close()
        s = xapwrap.index.SmartIndex(path, False)
        assert s.prefixMap == {'boo': 'BOO'}
        assert s.indexValueMap == {'uid': 0, 'uidREV': 1, 'hi': 2, 'hiREV': 3}

        ro = xapwrap.index.SmartReadOnlyIndex(path)
        assert s.prefixMap == ro.prefixMap
        assert s.indexValueMap == ro.indexValueMap


    def test_Sorting(self):
        path = self.mktemp()
        s = xapwrap.index.SmartIndex(path, True)
        docs = [Document(TextField('hi there'), uid=2, sortFields = SortKey('size', 99)),
                Document(TextField('hi there'), uid=3, sortFields = SortKey('size', 3)),
                Document(TextField('hi there'), uid=4, sortFields = SortKey('size', 10))]
        for d in docs:
            s.index(d)

        s.flush()
        result = s.search('hi', 'size', sortAscending=True)
        for uid, res in zip([3,4,2], result):
            assert uid==res['uid']

        result = s.search('hi', 'size', sortAscending=False)
        for uid, res in zip([2,4,3], result):
            assert uid==res['uid']

    def test_Values(self):
        path = self.mktemp()
        s = xapwrap.index.SmartIndex(path, True)
        docs = [Document(TextField('hi there'),
                         uid=2,
                         values = Value('thisvalue', 'blue'),
                         sortFields = SortKey('size', 99)),
                Document(TextField('hi there'),
                         uid=3,
                         values = [Value('thisvalue', 'red'), Value('thatvalue', 'funny')],
                         sortFields = SortKey('size', 3)),
                Document(TextField('hi there'),
                         uid=4,
                         sortFields = SortKey('size', 10))]
        for d in docs:
            s.index(d)

        s.flush()
        result = s.search('hi', 'size', sortAscending=True, valuesWanted=['thisvalue', 'thatvalue'])
        expectedVals = [{'thisvalue':'red', 'thatvalue':'funny'},
                      {'thisvalue':'', 'thatvalue':''} ,
                      {'thisvalue':'blue', 'thatvalue':''}]
        for vals, res in zip(expectedVals, result):
            assert res['values']==vals

    def test_GoodOrdering(self):
        docs = [Document(uid = 2, sortFields = SortKey('date', 'foo')),
                Document(uid = 3, sortFields = SortKey('issue', 3)),
                Document(uid = 4, sortFields = SortKey('dob', '2004-02-01'))]
        path1 = self.mktemp()
        path2 = self.mktemp()
        db1 = xapwrap.index.SmartIndex(path1, True)
        db2 = xapwrap.index.SmartIndex(path2, True)
        for d in docs:
            db1.index(d)
        db1.close()
        for i in range(len(docs))[::-1]:
            db2.index(docs[i])
        db2.close()
        assert db1.indexValueMap != db2.indexValueMap
        self.assertRaises(xapwrap.index.InconsistantIndexCombination,
                       xapwrap.index.SmartReadOnlyIndex, path1, path2)

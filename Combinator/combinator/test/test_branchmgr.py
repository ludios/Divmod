
"""
This module contains tests for combinator.branchmgr.
"""

import os, sys, StringIO

from twisted.trial.unittest import TestCase
from twisted.python.filepath import FilePath

from combinator.branchmgr import BranchManager, subversionURLExists
from combinator.subversion import createSubversionRepository


class SubversionUtilitiesTests(TestCase):
    """
    Tests to more or less general subversion-related functionality.
    """
    def setUp(self):
        """
        Compute the path and URL to a subversion repository which can be
        tested against and set up standard out to be recorded and hidden.
        """
        self.repository = FilePath(self.mktemp())
        createSubversionRepository(self.repository, {'foo': {}})
        self.url = 'file://' + self.repository.path
        self.stdout = sys.stdout
        sys.stdout = StringIO.StringIO()


    def tearDown(self):
        """
        Restore the normal standard out behavior.
        """
        sys.stdout = self.stdout


    def test_subversionURLExists(self):
        """
        L{subversionURLExists} should return True if given an URL which does
        exist.
        """
        self.assertTrue(subversionURLExists(self.url))


    def test_subversionURLDoesNotExist(self):
        """
        L{subversionURLExists} should return False if given an URL which
        does not exist.
        """
        self.assertFalse(subversionURLExists(self.url + '/bar'))



class BranchManagerTests(TestCase):
    """
    Tests for the BranchManager object.
    """

    def setUp(self):
        """
        Start keeping a record of all changed environment variables.
        """
        self.changedEnv = {}


    def changeEnvironment(self, key, value):
        """
        Change an environmnt variable such that it will be set back to its
        previous value at the end of the test.
        """
        self.changedEnv[key] = os.environ[key]
        os.environ[key] = value


    def tearDown(self):
        """
        Change back all environment variables altered during the course of this
        test.
        """
        for k, v in self.changedEnv.items():
            os.environ[k] = v


    def test_creation(self):
        """
        Verify that a newly-created branch manager can locate the paths it
        needs to do things.
        """
        b = BranchManager()
        self.assertNotEqual(b.svnProjectsDir, None)
        self.assertNotEqual(b.sitePathsPath, None)
        self.assertNotEqual(b.binCachePath, None)


    def test_projectsEnvironment(self):
        """
        Verify that BranchManager draws from the environment for the projects
        path.
        """
        self.changeEnvironment("COMBINATOR_PROJECTS", "somedir")
        b = BranchManager()
        self.assertEqual(b.svnProjectsDir, "somedir")


    def test_pathsEnvironment(self):
        """
        Verify that BranchManager draws from the environment for the paths
        path.
        """
        self.changeEnvironment("COMBINATOR_PATHS", "pathdir")
        b = BranchManager()
        self.assertEqual(b.sitePathsPath, os.path.abspath("pathdir"))
        self.assertEqual(b.binCachePath, "pathdir/bincache")


    def _perUserSitePackages(self, home):
        """
        Construct the path to the user-specific site-packages path.
        """
        return os.path.abspath(os.path.join(
            home, '.local', 'lib', 'python%d.%d' % tuple(sys.version_info[:2]),
            'site-packages'))


    def test_userSitePackages(self):
        """
        L{BranchManager.getPaths} should return an iterable which has as an
        element the user-specific site-packages directory, if that directory
        exists.
        """
        home = self.mktemp()
        sitePackages = self._perUserSitePackages(home)
        os.makedirs(sitePackages)
        self.changeEnvironment('HOME', home)
        b = BranchManager()
        self.assertIn(sitePackages, list(b.getPaths()))


    def test_missingUserSitePackages(self):
        """
        L{BranchManager.getPaths} should return an iterable which does not
        have as an element the user-specific site-packages directory, if
        that directory does not exist.
        """
        home = self.mktemp()
        self.changeEnvironment('HOME', home)
        b = BranchManager()
        self.assertNotIn(self._perUserSitePackages(home), list(b.getPaths()))



def _uri(repository, *branch):
    """
    Return a I{file} URI for the given branch of the given repository.
    """
    return 'file://' + reduce(FilePath.child, branch, repository).path



class ChangeBranchTests(TestCase):
    """
    Tests for L{BranchManager.changeProjectBranch}.
    """
    def setUp(self):
        """
        Create a branch manager with temporary directories for all its working
        filesystem paths.
        """
        self.paths = self.mktemp()
        self.projects = self.mktemp()
        os.makedirs(self.paths)
        os.makedirs(self.projects)
        self.manager = BranchManager(self.paths, self.projects)
        self.cwd = os.getcwd()

        self.repository = FilePath(self.mktemp())
        createSubversionRepository(
            self.repository, {'trunk': {},
                              'branches': {'foo': {}}})


    def tearDown(self):
        """
        Assert that the working directory has been restored to its original
        value if it was changed.
        """
        try:
            self.assertEqual(self.cwd, os.getcwd())
        finally:
            os.chdir(self.cwd)


    def test_trunkCheckoutWorkingDirectory(self):
        """
        The working directory should be the same before and after a call to
        L{BranchManager.changeProjectBranch} which does the initial trunk
        checkout of a project.
        """
        before = os.getcwd()
        self.manager.changeProjectBranch(
            'Quux', 'trunk', _uri(self.repository, 'trunk'))
        after = os.getcwd()
        self.assertEqual(before, after)


    def test_trunkCheckout(self):
        """
        L{BranchManager.changeProjectBranch} should create in the projects
        directory a checkout of trunk of the given project.
        """
        project = 'Quux'
        self.manager.changeProjectBranch(
            project, 'trunk', _uri(self.repository, 'trunk'))
        trunkWorkingCopy = os.path.join(self.paths, project, 'trunk')
        self.assertTrue(
            os.path.exists(trunkWorkingCopy),
            "%r did not exist." % (trunkWorkingCopy,))


    def test_trunkCheckoutWritesBranchFile(self):
        """
        L{BranchManager.changeProjectBranch} should write a new I{.bch} file
        for the given project when switching to trunk for the first time.
        """
        project = 'Quux'
        self.manager.changeProjectBranch(
            project, 'trunk', _uri(self.repository, 'trunk'))
        self.assertEqual(self.manager.currentBranchFor(project), 'trunk')


    def test_branchCheckoutChangesBranchFile(self):
        """
        L{BranchManager.changeProjectBranch} should rewrite an existing
        project's I{.bch} file when changing to a different branch.  The
        repository URI should not be required for this case.
        """
        project = 'Quux'
        branch = 'foo'

        # First get trunk
        self.manager.changeProjectBranch(
            project, 'trunk', _uri(self.repository, 'trunk'))

        # Then switch to the branch
        self.manager.changeProjectBranch(project, branch)

        self.assertEqual(self.manager.currentBranchFor(project), branch)



class MakeBranchTests(TestCase):
    """
    Tests for L{BranchManager.newProjectBranch}.
    """
    def setUp(self):
        """
        Create a branch manager with temporary directories for all its working
        filesystem paths.

        Also copy the test repository so that modifications may be made to it
        without affecting other tests.

        Also do the initial trunk checkout for the branch.
        """
        self.projectName = 'Quux'

        self.paths = self.mktemp()
        self.projects = self.mktemp()
        os.makedirs(self.paths)
        os.makedirs(self.projects)
        self.manager = BranchManager(self.paths, self.projects)

        self.repository = FilePath(self.mktemp())
        createSubversionRepository(
            self.repository, {'trunk': {},
                              'branches': {'foo': {}}})

        self.manager.changeProjectBranch(
            self.projectName, 'trunk', _uri(self.repository, 'trunk'))


    def test_changeCurrentBranch(self):
        """
        L{BranchManager.newProjectBranch} should change the current branch of
        the given project to the newly created branch.
        """
        branch = 'bar'
        self.manager.newProjectBranch(self.projectName, branch)
        self.assertEqual(
            self.manager.currentBranchFor(self.projectName), branch)


    def test_rejectDuplicateBranch(self):
        """
        L{BranchManager.newProjectBranch} should refuse to copy trunk into an
        existing branch.
        """
        existingBranch = 'foo'
        self.assertRaises(
            ValueError,
            self.manager.newProjectBranch, self.projectName, existingBranch)

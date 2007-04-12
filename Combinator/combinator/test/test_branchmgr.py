
"""
This module contains tests for combinator.branchmgr.
"""

import os

from twisted.trial.unittest import TestCase

from combinator.branchmgr import BranchManager

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
        self.assertEqual(b.sitePathsPath, "pathdir")
        self.assertEqual(b.binCachePath, "pathdir/bincache")

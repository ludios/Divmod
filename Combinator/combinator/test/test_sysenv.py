
"""
Tests for Combinator's environment-manipulation features.
"""

from twisted.trial.unittest import TestCase

from combinator.sysenv import Env, generatePathVariable
from StringIO import StringIO

class EnvironmentManipulatorTest(TestCase):
    """
    Tests to verify that Combinator's environment functions tests work
    properly.
    """

    def setUp(self):
        """
        Create an environment manipulator attached to mock objects.
        """
        self.stream = StringIO()
        self.envdict = {"PATH": "/usr/local/bin:/bin:/usr/bin:b:c:a"}
        self.env = Env(self.stream, self.envdict)


    def exportEnvironment(self):
        """
        Export the environment in a structured way and parse the output.
        """
        self.env.export('unknown')
        n = {}
        for line in self.stream.getvalue().splitlines():
            if line.startswith('export '):
                varset = line[len('export '):]
                strkey, strval = varset.split("=", 1)
                strval = strval.strip(";")
                strval = eval(strval)
                n[strkey] = strval
        return n


    def test_noPathReordering(self):
        """
        Verify that the Env object doesn't destructively re-order paths.
        """
        self.env.postPath("PATH", "y", "x")
        newEnv = self.exportEnvironment()
        self.assertEquals(newEnv['PATH'], self.envdict['PATH']+':y:x')


    def test_twoVariables(self):
        """
        Verify that more than one variable can be set at a time.
        """
        self.env["HELLO_WORLD"] = "0"
        self.env["GREETINGS_PROGRAM"] = "1"
        newEnv = self.exportEnvironment()
        self.assertEquals(newEnv, dict(HELLO_WORLD="0",
                                       GREETINGS_PROGRAM="1"))


class EnvironmentInteractionTest(TestCase):
    """
    These tests verify the behavior of functions which set up the environment.
    """

    def test_combinatorEnvironment(self):
        """
        Verify that generatePathVariable will set the appropriate Combinator
        environment variables.
        """
        e = Env(StringIO(), {})
        generatePathVariable(e, "alpha", "beta", StringIO())
        self.assertEquals(e.d['COMBINATOR_PROJECTS'], "alpha")
        self.assertEquals(e.d['COMBINATOR_PATHS'], "beta")

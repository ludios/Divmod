
import sys
import os

from combinator.branchmgr import theBranchManager
theBranchManager.addPaths()

for key in sys.modules.keys():
    # Unload all Combinator modules that had to be loaded in order to call
    # addPaths().  Although the very very beginning of this script needs to
    # load the trunk combinator (or whichever one your shell points at), once
    # the path has been set up, newer versions of combinator may be used; for
    # example, the 'whbranch', 'chbranch' and 'mkbranch' commands should all
    # import Combinator from the current Divmod branch.  This is especially
    # required so that Combinator's tests can be run on the currently-active
    # Combinator rather than the one responsible for setting up the
    # environment.
    if key == 'combinator' or key.startswith('combinator'):
        del sys.modules[key]

# Install stuff as a user, by default.

if sys.platform != 'darwin':
    # For use with setup.py...

    if sys.platform.startswith('win'):
        execprefix = os.path.abspath(os.path.expanduser("~/Python"))
    else:
        # Don't exactly know how Darwin fits in here - I think distutils is
        # buggy...?
        execprefix = os.path.abspath(os.path.expanduser("~/.local"))

    import sys

    class DistSysProxy:
        def __getattr__(self, attr):
            if attr in ('prefix', 'exec_prefix'):
                return execprefix
            else:
                return getattr(sys, attr)

    sys.modules['distutils.command.sys'] = DistSysProxy()

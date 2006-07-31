
import sys
import os

from combinator.branchmgr import init
init()

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

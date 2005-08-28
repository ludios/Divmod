
import sys
import os
import warnings

def splitall(p):
    car, cdr = os.path.split(p)
    if not cdr:
        return [car]
    else:
        return splitall(car) + [cdr]

def initialize():
    # Am I somewhere I recognize?
    saf = splitall(__file__)
    if not saf[-4:-1] == ['Divmod', 'trunk', 'Combinator']:
        warnings.warn(
            'Combinator sitecustomize located outside of Combinator directory, aborting')
        print saf
        return

    from combinator import branchmgr
    branchmgr.init(os.path.join(*saf[:-4]))

initialize()

# Install stuff as a user, by default.

if sys.platform != 'darwin':
    # For use with setup.py...

    if sys.platform.startswith('win'):
        execprefix = os.path.abspath(os.path.expanduser("~/Python"))
    else:
        # Don't exactly know how Darwin fits in here - I think distutils is
        # buggy...?
        execprefix = os.path.abspath(os.path.expanduser("~/.local"))

    import distutils.command.install

    class DistSysProxy:
        def __getattr__(self, attr):
            if attr in ('prefix', 'exec_prefix'):
                return execprefix
            else:
                return getattr(sys, attr)

    distutils.command.install.sys = DistSysProxy()

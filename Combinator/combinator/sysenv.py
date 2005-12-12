#!/usr/bin/env python

import sys
import os

from combinator import branchmgr

PATHVARS = 'PYTHONPATH', 'PATH', 'LD_LIBRARY_PATH', 'PATHEXT'

def uniq(l):
    tmpd = {}
    nl = []
    for x in l:
        if not tmpd.has_key(x):
            nl.append(x)
            tmpd[x] = 1
    return nl

class Env:
    def __init__(self):
        self._d = {}
        for k, v in os.environ.items():
            if k in PATHVARS:
                v = [(0, x) for x in uniq(v.split(os.pathsep)) if x]
            self._d[k] = v
        self.d = {}

    def __setitem__(self, k, v):
        self.d[k] = v

    def setupList(self, k):
        if not self.d.has_key(k):
            if self._d.has_key(k):
                self.d[k] = self._d[k]
            else:
                self.d[k] = []

    def prePath(self, k, *paths):
        self.setupList(k)
        for path in paths:
            self.d[k].insert(0, (-1, path))

    def postPath(self, k, *paths):
        self.setupList(k)
        for path in paths:
            self.d[k].append((1, path))

    def export(self, how):
        z = self.d.items()
        z.sort()
        if how == 'emacs':
            fstr = '(setenv "%s" "%s")'
            ffunc = lambda x: x.replace('"', '\\"')
        else:
            ffunc = repr
            if how == 'tcsh':
                fstr = 'setenv %s %s ;'
            elif how == 'bat':
                ffunc = lambda x: x # Windows does not like quoting in SET
                                    # lines at *all*
                fstr = 'set %s=%s'
            else:
                fstr = 'export %s=%s '
        for k, v in z:
            if isinstance(v, list):
                v.sort()
                v = os.pathsep.join(uniq([x[1] for x in v]))
            print fstr % (k, ffunc(v))


def generatePythonPathVariable(nv):
    nv.prePath('PYTHONPATH', os.path.split(os.path.split(__file__)[0])[0])

def generatePathVariable(nv):
    from combinator import branchmgr
    # since we're probably bootstrapping we need to make sure path entries are
    # set up for this one run... this is a harmless no-op if not.
    branchmgr.init()

    nv.prePath('PATH', branchmgr.theBranchManager.binCachePath)
    if os.name == 'nt':
        nv.postPath('PATHEXT', '.PY')
    userBinPath = os.path.abspath(
        os.path.expanduser("~/.local/bin"))
    if os.path.exists(userBinPath):
        nv.prePath("PATH", userBinPath)

    # XXX move to separate command?
    if not os.path.isdir(branchmgr.theBranchManager.binCachePath):
        os.makedirs(branchmgr.theBranchManager.binCachePath)
    for ent in sys.path:
        branchBinDir = os.path.join(ent, 'bin')
        if os.path.isdir(branchBinDir):
            for binary in os.listdir(branchBinDir):
                if not binary.startswith('.'):
                    dst = os.path.join(branchmgr.theBranchManager.binCachePath,
                                       binary)
                    if os.name == 'nt':
                        dst += '.py'
                    src = os.path.join(
                        os.path.dirname(os.path.dirname(__file__)),
                        'bin', 'cham.py')
                    if not os.path.exists(dst):
                        sys.stderr.write('link: %r => %r\n <on account of %r>\n' % (dst, src, ent))
                        file(dst, 'w').write(file(src).read())
                        if os.name != 'nt':
                            os.chmod(dst, 0755)

def export():
    e = Env()
    generatePythonPathVariable(e)
    generatePathVariable(e)
    if sys.platform == 'win32':
        how = 'bat'
    else:
        how = 'sh'
    e.export(how)

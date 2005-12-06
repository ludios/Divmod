#!/usr/bin/python

import os
import sys

from combinator import branchmgr

def naturalName(n):
    return os.path.splitext(os.path.split(n)[1])[0]

def remain(argv):
    # sys.stderr.write('<chameleon script activated: %r>\n' % (argv))
    cmdname = naturalName(argv[0])
    for p in sys.path:
        binpath = os.path.join(p, 'bin', cmdname)
        if os.path.exists(binpath):
            break
    else:
        sys.stderr.write('<chameleon could not change form!>\n')
        os._exit(254)

    newargz = [binpath] + argv[1:]
    # sys.stderr.write('<chameleon changing form: %r>\n' % (newargz,))
    if os.name == 'nt':
        newargz.insert(0, sys.executable)
        binpath = sys.executable
        newargz = map(branchmgr._cmdLineQuote, newargz)
        binpath = branchmgr._cmdLineQuote(binpath)
        wincmd = ' '.join(newargz)
        os.system(wincmd)
    else:
        os.execv(binpath, newargz)

if __name__ == '__main__':
    remain(sys.argv[1:])

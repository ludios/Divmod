#!/usr/bin/python

import os
import sys
import signal

from combinator import branchmgr

def naturalName(n):
    return os.path.splitext(os.path.split(n)[1])[0]

def nostop(*a):
    pass

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
        wincmd = ' '.join(newargz[1:])
        import msvcrt
        try:
            # There is probably a better 'are we running in a GUI, ie, is
            # os.system going to be completely broken' test, but I have no idea
            # what it is.
            osfh = msvcrt.get_osfhandle(0)
        except IOError:
            try:
                import win32pipe
            except ImportError:
                print "Non-console I/O is broken on win32"
                print "Workaround requires pywin32"
                print "http://sourceforge.net/project/showfiles.php?group_id=78018"
                os._exit(2)
            else:
                opipe = win32pipe.popen(' '.join(newargz), 'r')
                while 1:
                    byte = opipe.read(1)
                    if not byte:
                        break
                    sys.stdout.write(byte)
                    sys.stdout.flush()
        else:
            signal.signal(signal.SIGINT, nostop) # ^C on Windows suuuuuuuucks
            exstat = os.system(' '.join(newargz))
            os._exit(exstat)
    else:
        os.execv(binpath, newargz)

if __name__ == '__main__':
    remain(sys.argv[1:])

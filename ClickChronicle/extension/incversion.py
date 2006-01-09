#!/usr/bin/env python

from os import path

def getversion(fname):
    from xml.dom import minidom
    doc = minidom.parse(fname)
    (version,) = set(e.firstChild.nodeValue for e in
                        doc.getElementsByTagNameNS(
                            'http://www.mozilla.org/2004/em-rdf#', 'version'))
    return float(version)

def main(newversion=None, files=('install.rdf', 'update.rdf')):
    for fname in files:
        if newversion is None:
            curversion = getversion(fname)
            newversion = curversion + 0.1
        new = file(fname + '.tmpl').read() % dict(version=newversion)
        file(fname, 'w').write(new)

if __name__ == '__main__':
    from sys import argv

    if len(argv) == 2:
        newversion = argv[1]
    elif len(argv) == 1:
        newversion = None
    else:
        raise RuntimeError('expected zero or one arguments')

    main(*argv[1:])

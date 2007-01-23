from xml.dom import minidom
from os import path as ospath

def checkpaths(contentloc, paths, appname='clickchronicle', contentdir='content'):
    prefix = 'chrome://%s/%s' % (appname, contentdir)
    for path in paths:
        doc = minidom.parse(path)
        for script in doc.getElementsByTagName('script'):
            src = script.getAttribute('src')
            if not src.startswith(prefix):
                print 'file %s has invalid/relative script URI %s' % (path, src)
                continue

            suffix = src[len(prefix):]
            if '/' != ospath.sep:
                suffix = suffix.replace('/', ospath.sep)
            suffix = suffix.lstrip(ospath.sep)

            if not ospath.exists(ospath.join(contentloc, suffix)):
                print 'file %s has script URI with non-existant target: %s' % (path, src)

if __name__ == '__main__':
    from sys import argv
    checkpaths(argv[1], argv[2:])

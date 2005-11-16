from nevow import tags, loaders
from twisted.internet.defer import maybeDeferred
from twisted.python.util import mergeFunctionMetadata
from twisted.python import util

# staticTemplate and makeScriptTag are used by clickapp and public page
# moved in here to avoid circular import issues
staticTemplate = lambda fname: loaders.xmlfile(util.sibpath(__file__, "static/html/" + fname))

def makeScriptTag(src):
    return tags.script(type="application/x-javascript", src=src)

def maybeDeferredWrapper(f):
    """nicer than maybeDeferred.__get__"""
    def wrapped(*a, **k):
        return maybeDeferred(f, *a, **k)
    return mergeFunctionMetadata(f, wrapped)

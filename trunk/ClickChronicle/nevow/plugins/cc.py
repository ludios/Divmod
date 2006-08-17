from twisted.python import util
from nevow import athena
import clickchronicle

def _f(*sibling):
    return util.sibpath(clickchronicle.__file__, '/'.join(sibling))

mantissa = athena.JSPackage({
    u'ClickChronicle': _f('static', 'js', 'cc.js'),
    u'ClickChronicle.LiveClicks': _f('static', 'js', 'live-clicks.js'),
    u'ClickChronicle.BookmarkList': _f('static', 'js','bookmark-list.js') })


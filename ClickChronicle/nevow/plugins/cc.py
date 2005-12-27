from twisted.python import filepath
from nevow import athena

import clickchronicle

mantissa = athena.JSPackage({
    u'ClickChronicle': filepath.FilePath(clickchronicle.__file__).parent().child('static').child('js').child('live-clicks.js').path})

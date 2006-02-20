
from twisted.python import filepath

from nevow import athena

import radical

def path(file):
    return filepath.FilePath(radical.__file__).parent().child('static').child('js').child(file + '.js').path

radjs = athena.JSPackage({
    'Radical': path('radical'),
    'Radical.Geometry': path('geometry'),
    'Radical.World': path('world')})


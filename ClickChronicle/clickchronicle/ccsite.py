from zope.interface import implements
from axiom.item import Item
from axiom import attributes
from xmantissa.ixmantissa import ISiteRootPlugin
from xmantissa.website import PrefixURLMixin, WebSite
from nevow import loaders, rend

class RootResource( rend.Page ):
    docFactory = loaders.xmlfile( 'root.xml' )
    addSlash = True

    #def child_( self, ctx ):
    #    return self
    
# not sure about this
class ClickChronicleWebSite( Item, PrefixURLMixin ):
    implements( ISiteRootPlugin )
    typeName = 'clickchronicle_website'
    schemaVersion = 1
    prefixURL = ''

    # ?
    users = attributes.integer( default = 0 )

    def createResource( self ):
        print '....called....................'
        return RootResource()

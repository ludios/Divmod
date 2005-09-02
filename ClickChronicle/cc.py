from axiom.item import Item
from axiom import attributes
from zope.interface import implements
from xmantissa.webnav import Tab
from xmantissa.ixmantissa import INavigableElement, IBenefactor
from xmantissa.webadmin import ParentCounterMixin
from nevow import loaders, rend, livepage
from twisted.python.components import registerAdapter
from xmantissa.webadmin import WebSite, PrivateApplication

#class ClickChronicleApplication( PrivateApplication ):
    #implements( INavigableElement )
    #typeName = 'clickchronicle_application'
    #schemaVersion = 1
    #urlCount = attributes.integer( default = 0 )

    #def install( self ):
    #    self.store.powerUp( self, INavigableElement )

    #def getTabs( self ):
    #    return [Tab('Admin', self.storeID, 0.0,
    #                [Tab('Magical', self.storeID, 0.1)])]

    #def createResource( self, a, b, c, d, e, f, g ):
    #    pass
#    pass
from xmantissa.ixmantissa import INavigableFragment
class Visit( Item ):
    timestamp = attributes.timestamp()
    url = attributes.text()

    schemaVersion = 1
    typeName = 'visit'

from nevow.inevow import IResource, IQ

class LinkList( rend.Page ):
    implements( IResource )
    docFactory = loaders.xmlfile( 'linklist.xml' )

    def __init__( self, *a, **k ):
        rend.Page.__init__( self, *a, **k )
        self.store = self.original.store

    def data_links( self, ctx, data ):
        for visit in self.store.query( Visit ):
            yield dict( timestamp = visit.timestamp, url = visit.url )

class ClickChronicleApplication( Item, ParentCounterMixin ):
    implements( INavigableElement )
    typeName = 'clickchronicle_application'
    schemaVersion = 1
    urlCount = attributes.integer( default = 0 )

    def install( self ):
        self.store.powerUp( self, INavigableElement )

    def getTabs( self ):
        return [Tab('Admin', self.storeID, 0.0,
                    [Tab('Magical', self.storeID, 0.1)])]
static = lambda value : lambda *a, **k: value

class ClickChronicleFragment( rend.Fragment ):
    fragmentName = 'click-chronicle-fragment'
    live = True
    docFactory = loaders.xmlfile( 'linklist.xml' )
    head = static( "" )
   
registerAdapter( ClickChronicleFragment, ClickChronicleApplication, INavigableFragment )
from nevow import inevow

class URLGrabber( rend.Page ):
    def __init__( self, store ):
        self.store = store
        
    def renderHTTP( self, ctx ):
        urlpath = inevow.IRequest( ctx ).URLPath()
        url = dict( urlpath.queryList() ).get( 'url' )
        if url is not None:
            # put url as Visit in self.store
            print '** got', url
        else:
            # explode
            print '** missing query param "url"'
from xmantissa.website import PrefixURLMixin
from xmantissa.ixmantissa import ISiteRootPlugin
class ClickRecorder( Item, PrefixURLMixin ):
    schemaVersion = 1
    implements( ISiteRootPlugin )
    typeName = 'clickrecorder'
    someAttribute = attributes.integer( default = 0 )
    prefixURL = 'private/record'

    def install( self ):
        self.store.powerUp( self, ISiteRootPlugin )

    def createResource( self ):
        return URLGrabber( self.store )

class ClickChronicleBenefactor( Item ):
    implements( IBenefactor )
    typeName = 'clickchronicle_benefactor'
    schemaVersion = 1

    endowed = attributes.integer( default = 0 )

    def endow(self, ticket, avatar):
        self.endowed += 1
        WebSite( store = avatar ).install()
        PrivateApplication( store = avatar ).install()
        ClickChronicleApplication( store = avatar ).install()
        ClickRecorder( store = avatar ).install()
        #for item in ( WebSite, PrivateApplication ):
        #    item( store = avatar ).install()

from axiom.item import Item
from axiom import attributes
from zope.interface import implements
from xmantissa.webnav import Tab
from xmantissa import ixmantissa
from xmantissa.webadmin import ParentCounterMixin
from nevow import loaders, rend, livepage, inevow
from twisted.python.components import registerAdapter
from xmantissa.webadmin import WebSite, PrivateApplication
from xmantissa.website import PrefixURLMixin
from epsilon.extime import Time
from datetime import datetime

class Visit( Item ):
    timestamp = attributes.timestamp()
    url = attributes.bytes()
    title = attributes.bytes()

    schemaVersion = 1
    typeName = 'visit'

class ClickChronicleApplication( Item, ParentCounterMixin ):
    implements( ixmantissa.INavigableElement )
    typeName = 'clickchronicle_application'
    attribute = attributes.integer( default = 0 ) # ?
    schemaVersion = 1

    def install( self ):
        self.store.powerUp( self, ixmantissa.INavigableElement )

    def getTabs( self ):
        return [Tab('My Account', self.storeID, 0.0,
                    [Tab('My Clicks', self.storeID, 0.0),
                     Tab('My Something Else', self.storeID, 0.0)])]
        
class LinkListFragment( rend.Fragment ):
    fragmentName = 'link-list-fragment'
    title = ''
    live = True
    
    def head( self ):
        return ''

    def data_links( self, ctx, data ):
        store = self.original.store
        for visit in store.query( Visit, sort = Visit.timestamp.descending ):
            yield dict( url = visit.url, 
                        timestamp = visit.timestamp.asHumanly(),
                        title = visit.title )

registerAdapter( LinkListFragment, 
                 ClickChronicleApplication, 
                 ixmantissa.INavigableFragment )

class URLGrabber( rend.Page ):
    def __init__( self, recorder ):
        self.recorder = recorder
        
    def renderHTTP( self, ctx ):
        urlpath = inevow.IRequest( ctx ).URLPath()
        qargs = dict( urlpath.queryList() )
        url = qargs.get( 'url' )
        if url is not None:
            self.recorder.urlCount += 1
            Visit(store = self.recorder.store,
                  url = url,
                  timestamp = Time.fromDatetime( datetime.now() ),
                  title = qargs.get( 'title', 'Untitled' ))
        return ''
            
class ClickRecorder( Item, PrefixURLMixin ):
    schemaVersion = 1
    implements( ixmantissa.ISiteRootPlugin )
    typeName = 'clickrecorder'
    urlCount = attributes.integer( default = 0 )
    prefixURL = 'private/record'

    def install( self ):
        self.store.powerUp( self, ixmantissa.ISiteRootPlugin )

    def createResource( self ):
        return URLGrabber( self )

class ClickChronicleBenefactor( Item ):
    implements( ixmantissa.IBenefactor )
    typeName = 'clickchronicle_benefactor'
    schemaVersion = 1

    endowed = attributes.integer( default = 0 )

    def endow(self, ticket, avatar):
        self.endowed += 1
        for item in (WebSite, PrivateApplication, 
                     ClickChronicleApplication, ClickRecorder):
            item( store = avatar ).install()

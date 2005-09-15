from twisted.application import service
from axiom import store

import xmantissa.website
import xmantissa.webadmin
import xmantissa.signup
import signup_hack
from clickchronicle import visit, clickapp

application = service.Application('ClickChronicle')
store.StorageService( 'cchronicle.axiom' ).setServiceParent(application)

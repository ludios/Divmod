from twisted.application import service
from axiom import store

import xmantissa.website
import xmantissa.webadmin
import xmantissa.signup
from clickchronicle import visit, clickapp, signup_hack

application = service.Application('ClickChronicle')
store.StorageService( 'cchronicle.axiom' ).setServiceParent(application)

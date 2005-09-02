from twisted.application import service
from axiom import store

import xmantissa.website
import xmantissa.webadmin
import xmantissa.signup
from ccsite import ClickChronicleWebSite
from cc import ClickChronicleBenefactor

application = service.Application('ClickChronicle')
store.StorageService( 'cchronicle.axiom' ).setServiceParent(application)

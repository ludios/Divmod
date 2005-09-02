from axiom.store import Store
from axiom.userbase import LoginSystem
from xmantissa.webapp import PrivateApplication
from xmantissa.website import WebSite
from xmantissa.signup import FreeTicketSignup, TicketBooth
from cc import ClickChronicleBenefactor
from ccsite import ClickChronicleWebSite
siteStore = Store( 'cchronicle.axiom', debug = True )

# not sure about this inheritance, it looks like it makes sense
def installSite():
    LoginSystem( store = siteStore ).install()
    
    siteStore.checkpoint()
     
    WebSite( store = siteStore, portno = 8080 ).install()
    ClickChronicleWebSite( store = siteStore ).install() 
    
    booth = TicketBooth( store = siteStore )
    booth.install()

    ccBenefactor = ClickChronicleBenefactor( store = siteStore )

    FreeTicketSignup( store = siteStore,
                      benefactor = ccBenefactor,
                      prefixURL = u'signup',
                      booth = booth ).install()

siteStore.transact( installSite )

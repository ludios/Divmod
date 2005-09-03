from axiom.store import Store
from axiom.userbase import LoginSystem
from axiom.item import Item
from xmantissa.webapp import PrivateApplication
from xmantissa.website import WebSite
from xmantissa.signup import TicketBooth
from cc import ClickChronicleBenefactor
from ccsite import ClickChronicleWebSite
from signup_hack import EmaillessTicketSignup

siteStore = Store( 'cchronicle.axiom', debug = True )

def installSite():
    LoginSystem( store = siteStore ).install()
    
    siteStore.checkpoint()
     
    WebSite( store = siteStore, portno = 8080 ).install()
    ClickChronicleWebSite( store = siteStore ).install() 
    
    booth = TicketBooth( store = siteStore )
    booth.install()

    ccBenefactor = ClickChronicleBenefactor( store = siteStore )

    EmaillessTicketSignup( store = siteStore,
                           benefactor = ccBenefactor,
                           prefixURL = u'signup',
                           booth = booth ).install()

siteStore.transact( installSite )

from axiom.store import Store
from axiom.userbase import LoginSystem
from axiom.item import Item
from xmantissa.webapp import PrivateApplication
from xmantissa.website import WebSite, StaticSite
from xmantissa.signup import TicketBooth
from cc import ClickChronicleBenefactor
from ccsite import ClickChronicleWebSite
from signup_hack import EmaillessTicketSignup

siteStore = Store( 'cchronicle.axiom', debug = True )

def installSite():
    LoginSystem( store = siteStore ).installOn(siteStore)

    siteStore.checkpoint()

    WebSite( store = siteStore, portno = 8080 ).installOn(siteStore)
    ClickChronicleWebSite( store = siteStore ).installOn(siteStore)
    StaticSite( store = siteStore, prefixURL = u'static', 
                staticContentPath = u'static' ).installOn(siteStore)

    booth = TicketBooth( store = siteStore )
    booth.installOn(siteStore)

    ccBenefactor = ClickChronicleBenefactor( store = siteStore )

    EmaillessTicketSignup( store = siteStore,
                           benefactor = ccBenefactor,
                           prefixURL = u'signup',
                           booth = booth ).installOn(siteStore)

siteStore.transact( installSite )

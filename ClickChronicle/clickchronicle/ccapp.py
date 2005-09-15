from axiom.store import Store
from axiom.userbase import LoginSystem
from xmantissa.website import WebSite, StaticSite
from xmantissa.signup import TicketBooth
from clickchronicle.clickapp import ClickChronicleBenefactor
from signup_hack import EmaillessTicketSignup

siteStore = Store('cchronicle.axiom', debug = True)

def installSite():
    LoginSystem(store = siteStore).installOn(siteStore)

    siteStore.checkpoint()

    WebSite(store = siteStore, portno = 8080).installOn(siteStore)
    StaticSite(store = siteStore, prefixURL = u'static', 
               staticContentPath = u'static').installOn(siteStore)

    booth = TicketBooth(store = siteStore)
    booth.installOn(siteStore)

    ccBenefactor = ClickChronicleBenefactor(store = siteStore)

    EmaillessTicketSignup(store = siteStore,
                          benefactor = ccBenefactor,
                          prefixURL = u'signup',
                          booth = booth).installOn(siteStore)

siteStore.transact(installSite)

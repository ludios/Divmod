
import os

from twisted.python.util import sibpath
from twisted.python import filepath

from vertex.scripts import certcreate

from axiom.store import Store
from axiom.userbase import LoginSystem
from axiom.scheduler import Scheduler

from xmantissa.website import WebSite, StaticSite
from xmantissa.signup import TicketBooth

from clickchronicle.clickapp import ClickChronicleBenefactor
from clickchronicle.signup_hack import EmaillessTicketSignup

def installSite(siteStore):
    LoginSystem(store = siteStore).installOn(siteStore)

    WebSite(
        store = siteStore,
        portNumber = 8080,
        securePortNumber = 8443,
        certificateFile = 'server.pem').installOn(siteStore)
    StaticSite(store = siteStore, prefixURL = u'static',
               staticContentPath = sibpath(__file__, u'static')).installOn(siteStore)

    booth = TicketBooth(store = siteStore)
    booth.installOn(siteStore)

    ccBenefactor = ClickChronicleBenefactor(store = siteStore)

    EmaillessTicketSignup(store = siteStore,
                          benefactor = ccBenefactor,
                          prefixURL = u'signup',
                          booth = booth).installOn(siteStore)

    Scheduler(store = siteStore).installOn(siteStore)

def main():
    if not os.path.exists('server.pem'):
        certcreate.main()
    siteStore = Store('cchronicle.axiom', debug = False)
    siteStore.transact(installSite, siteStore)

if __name__ == '__main__':
    main()

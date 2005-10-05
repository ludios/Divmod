
import os

from twisted.python.util import sibpath
from twisted.python import filepath
from twisted.cred import portal

from vertex.scripts import certcreate

from axiom.store import Store
from axiom.userbase import LoginSystem
from axiom.scheduler import Scheduler

from xmantissa.website import WebSite, StaticSite
from xmantissa.publicweb import PublicWeb
from xmantissa.signup import TicketBooth

from clickchronicle.clickapp import ClickChronicleBenefactor, ClickChroniclePublicPage
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

def installClickChronicleUser(siteStore):
    ls = portal.IRealm(siteStore)

    ccAvatar = ls.addAccount('clickchronicle', 'system', None)
    ccAvatarStore = ccAvatar.avatars.open()
    ClickChroniclePublicPage(store=ccAvatarStore).installOn(ccAvatarStore)

    PublicWeb(store=siteStore, prefixURL=u'', application=ccAvatar).installOn(siteStore)


def main():
    if not os.path.exists('server.pem'):
        certcreate.main()
    siteStore = Store('cchronicle.axiom', debug = False)

    def f():
        installSite(siteStore)
        installClickChronicleUser(siteStore)
    siteStore.transact(f)

if __name__ == '__main__':
    main()

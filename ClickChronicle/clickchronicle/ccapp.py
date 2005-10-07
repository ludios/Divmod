
import os

from twisted.python.util import sibpath
from twisted.python import filepath
from twisted.cred import portal

from vertex.scripts import certcreate

from axiom.store import Store
from axiom.userbase import LoginSystem
from axiom.scheduler import Scheduler

from xmantissa import endpoint
from xmantissa.website import WebSite, StaticSite
from xmantissa.publicweb import PublicWeb
from xmantissa.signup import TicketBooth, FreeTicketSignup

import clickchronicle
from clickchronicle.clickapp import ClickChronicleBenefactor, ClickChroniclePublicPage
from clickchronicle.signup_hack import EmaillessTicketSignup

DEV = False

def installSite(siteStore):
    LoginSystem(store = siteStore).installOn(siteStore)

    endpoint.UniversalEndpointService(store=siteStore).installOn(siteStore)

    WebSite(
        store = siteStore,
        portNumber = 8080,
        securePortNumber = 8443,
        certificateFile = 'server.pem').installOn(siteStore)
    StaticSite(store = siteStore, prefixURL = u'static',
               staticContentPath = sibpath(clickchronicle.__file__, u'static')).installOn(siteStore)

    booth = TicketBooth(
        store = siteStore,
        defaultTicketEmail = sibpath(clickchronicle.__file__, u'signup.eml'))
    booth.installOn(siteStore)

    ccBenefactor = ClickChronicleBenefactor(store = siteStore)

    if DEV:
        cls = EmaillessTicketSignup
    else:
        cls = FreeTicketSignup

    cls(store = siteStore,
        benefactor = ccBenefactor,
        prefixURL = u'signup',
        booth = booth).installOn(siteStore)

    Scheduler(store = siteStore).installOn(siteStore)

def installClickChronicleUser(siteStore):
    ls = portal.IRealm(siteStore)

    ccAvatar = ls.addAccount('clickchronicle', 'clickchronicle.com', None)
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

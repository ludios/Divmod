from twisted.internet import reactor, defer
from twisted.application.service import IService, Service
from twisted.cred.portal import IRealm, Portal
from twisted.cred.checkers import ICredentialsChecker
from twisted.python.components import registerAdapter
from nevow import livepage, tags
from axiom import userbase
from axiom.attributes import integer, inmemory, bytes, text, reference, timestamp
from axiom.item import Item, InstallableMixin
from axiom.slotmachine import hyper as super
from epsilon.extime import Time
from sine import sip, useragent
from xmantissa import ixmantissa, website, webapp, webnav
from zope.interface import implements

import time

class SIPConfigurationError(RuntimeError):
    """You specified some invalid configuration."""


class SIPServer(Item, Service):
    typeName = 'mantissa_sip_powerup'
    schemaVersion = 1
    portno = integer(default=5060)
    hostnames =  bytes()
    installedOn = reference()
    
    parent = inmemory()
    running = inmemory()
    name = inmemory()

    proxy = inmemory()
    port = inmemory()
    site = inmemory()

    def installOn(self, other):
        assert self.installedOn is None, "You cannot install a SIPServer on more than one thing"
        other.powerUp(self, IService)
        self.installedOn = other

    def privilegedStartService(self):
        realm = IRealm(self.store, None)
        if realm is None:
            raise SIPConfigurationError(
                'No realm: '
                'you need to install a userbase before using this service.')
        chkr = ICredentialsChecker(self.store, None)
        if chkr is None:
            raise SIPConfigurationError(
                'No checkers: '
                'you need to install a userbase before using this service.')
        portal = Portal(realm, [chkr])
        self.proxy = sip.Proxy(portal, self.hostnames.split(','))

        f = sip.SIPTransport(self.proxy, self.hostnames.split(','), self.portno)
        
        self.port = reactor.listenUDP(self.portno, f)

class TrivialRegistrarInitializer(Item, InstallableMixin):
    """
    ripoff of ClickChronicleInitializer
    """
    implements(ixmantissa.INavigableElement)

    typeName = 'sipserver_initializer'
    schemaVersion = 1
    
    installedOn = reference()
    domain = text()

    def installOn(self, other):
        super(TrivialRegistrarInitializer, self).installOn(other)
        other.powerUp(self, ixmantissa.INavigableElement)

    def getTabs(self):
        # This won't ever actually show up
        return [webnav.Tab('Preferences', self.storeID, 1.0)]

    def setLocalPartAndPassword(self, localpart, password):
        substore = self.store.parent.getItemByID(self.store.idInParent)
        for acc in self.store.parent.query(userbase.LoginAccount,
                                           userbase.LoginAccount.avatars == substore):
            userbase.LoginMethod(store=self.store.parent,
                                 localpart=unicode(localpart),
                                 internal=True,
                                 protocol=u'sip',
                                 verified=True,
                                 domain=self.domain,
                                 account=acc)
            acc.password = unicode(password)
            self._reallyEndow()
            return

    def _reallyEndow(self):
        avatar = self.installedOn
        avatar.findOrCreate(TrivialContact).installOn(avatar)
        avatar.powerDown(self, ixmantissa.INavigableElement)
        self.deleteFromStore()

class TrivialRegistrarInitializerPage(website.AxiomFragment):
    implements(ixmantissa.INavigableFragment)
    live = True
    fragmentName = 'trivial_registrar_initializer'

    def __init__(self, original):
        website.AxiomFragment.__init__(self, original)
        self.store = original.store

    def handle_setLocalPartAndPassword(self, ctx, localpart, password):
        for lm in self.original.store.query(userbase.LoginMethod,
                userbase.LoginMethod.localpart==localpart):
            return livepage.js.alert('SIP user by that name already exists! Please choose a different username')
        else:
            self.original.setLocalPartAndPassword(localpart, password)
            return livepage.js.alert('OMG! set the local part thing')

    def head(self):
        return tags.script(src='/static/sine/js/initializer.js',
                           type='text/javascript')

registerAdapter(TrivialRegistrarInitializerPage,
                TrivialRegistrarInitializer,
                ixmantissa.INavigableFragment)

class SineBenefactor(Item):
    implements(ixmantissa.IBenefactor)

    typeName = 'sine_benefactor'
    schemaVersion = 1
    domain=text()
    # Number of users this benefactor has endowed
    endowed = integer(default = 0)

    def endow(self, ticket, avatar):
        self.endowed += 1
        la = avatar.parent.findFirst(userbase.LoginAccount,
                avatars=avatar.parent.getItemByID(avatar.idInParent))

        avatar.findOrCreate(website.WebSite).installOn(avatar)
        avatar.findOrCreate(webapp.PrivateApplication).installOn(avatar)
        avatar.findOrCreate(TrivialRegistrarInitializer, domain=self.domain).installOn(avatar)


class TrivialContact(Item, InstallableMixin):
    implements(sip.IContact)

    typeName = "sine_trivialcontact"
    schemaVersion = 1

    physicalURL = bytes()
    expiryTime = timestamp()
    installedOn = reference()
    
    def installOn(self, other):
        super(TrivialContact, self).installOn(other)
        other.powerUp(self, sip.IContact)

    def registerAddress(self, physicalURL, expiryTime):
        self.physicalURL = physicalURL.toString()
        self.expiryTime = Time.fromPOSIXTimestamp(time.time() + expiryTime)
        return [(physicalURL, self.expiryTime)]
    
    def unregisterAddress(self, physicalURL):
        if self.physicalURL != physicalURL:
            raise ValueError, "what"
        self.physicalURL = None
        return [(physicalURL, 0)]
    def getRegistrationInfo(self):
        registered = False
        if self.physicalURL is not None:
            now = time.time()
            if now < self.expiryTime.asPOSIXTimestamp():
                registered = True
        if registered:
            return [(sip.parseURL(self.physicalURL), int(self.expiryTime.asPOSIXTimestamp() - now))]
        else:
            return defer.fail(sip.RegistrationError(480))

    def callIncoming(self, name, uri, caller):
        pass

    def callOutgoing(self, name, uri):
        pass


class SIPDispatcherService(Item, Service):
    typeName = 'sine_sipdispatcher_service'
    schemaVersion = 1
    portno = integer(default=5060)
    hostnames =  bytes()
    installedOn = reference()
    
    parent = inmemory()
    running = inmemory()
    name = inmemory()

    dispatcher = inmemory()
    proxy = inmemory()
    port = inmemory()
    site = inmemory()

    def installOn(self, other):
        assert self.installedOn is None, "You cannot install a SIPDispatcherService on more than one thing"
        other.powerUp(self, IService)
        self.installedOn = other

    def privilegedStartService(self):
        realm = IRealm(self.store, None)
        if realm is None:
            raise SIPConfigurationError(
                'No realm: '
                'you need to install a userbase before using this service.')
        chkr = ICredentialsChecker(self.store, None)
        if chkr is None:
            raise SIPConfigurationError(
                'No checkers: '
                'you need to install a userbase before using this service.')
        portal = Portal(realm, [chkr])
        self.proxy = sip.Proxy(portal)
        self.dispatcher = sip.SIPDispatcher(portal, self.proxy)
        f = sip.SIPTransport(self.dispatcher, self.hostnames.split(','), self.portno)
        
        self.port = reactor.listenUDP(self.portno, f)

# -*- test-case-name: clickchronicle.test -*-
import os

from zope.interface import classProvides

from twisted.python import usage, util
from twisted.cred import portal
from twisted import plugin

from vertex.scripts import certcreate

from axiom import iaxiom, errors as eaxiom, scheduler, userbase
from axiom.scripts import axiomatic

from xmantissa import signup, website, publicweb

from clickchronicle import clickapp, publicpage, prods

class ChronicleOptionsMixin:
    optParameters = [
        ('ticket-signup-url', None, 'signup', 'URL at which to place a ticket request page'),
        ('max-clicks', 'm', None, 'The maximum number of clicks to store for each user.'),
        ]

    didSomething = False

    def _benefactorAndSignup(self):
        s = self.parent.getStore()
        bene = s.findUnique(clickapp.ClickChronicleBenefactor)
        ticketSignup = s.findUnique(
            signup.FreeTicketSignup,
            signup.FreeTicketSignup.benefactor == bene)
        return bene, ticketSignup

class ClickStatsInterval(usage.Options, axiomatic.AxiomaticSubCommandMixin):
    longdesc = """
    Change the interval attribute of the system user's ClickStats item - 
    this determines the period within which click scores are updated.
    """

    optParameters = (('interval', 'i', None),
                     ('system-user', 'u', 'clickchronicle@clickchronicle.com'))

    def changeInterval(self, interval, systemUser):
        store = self.parent.getStore()
        loginSystem = portal.IRealm(store)
        (localpart, hostname) = unicode(systemUser).split('@')
        substore = loginSystem.accountByAddress(localpart, hostname).avatars.open()
        pp = substore.findFirst(publicpage.ClickChroniclePublicPage)
        pp.interval = interval

    def postOptions(self):
        if self['interval'] is None:
            raise usage.UsageError('--interval must be specified')
        self.changeInterval(int(self['interval']), self['system-user'])

class Install(usage.Options, axiomatic.AxiomaticSubCommandMixin):
    longdesc = """
    Install site-wide ClickChronicle requirements.  This includes
    such things as the Scheduler, LoginSystem, and WebSite.
    """

    optParameters = [
        ('system-user', 'u', 'clickchronicle@clickchronicle.com',
        'username@domain-format username to contain public site information (created if nonexistent'),
        ('public-url', 'p', '', 'URL at which to serve public ClickChronicle content'),
        ('signup-url', 's', 'signup', 'URL at which to offer free ticketted signup'),
        ]

    def log(self, message):
        print message

    def installClickChronicle(self, signupURL):
        s = self.parent.getStore()

        s.findOrCreate(scheduler.Scheduler).installOn(s)
        s.findOrCreate(userbase.LoginSystem).installOn(s)

        for ws in s.query(website.WebSite):
            break
        else:
            website.WebSite(
                store=s,
                portNumber=8080,
                securePortNumber=8443,
                certificateFile='server.pem').installOn(s)
            if not os.path.exists('server.pem'):
                certcreate.main([])

        s.findOrCreate(
            website.StaticSite,
            prefixURL=u'static',
            staticContentPath=util.sibpath(clickapp.__file__, u'static')).installOn(s)

        booth = s.findOrCreate(
            signup.TicketBooth,
            defaultTicketEmail=util.sibpath(clickapp.__file__, u'signup.eml'))
        booth.installOn(s)

        benefactor = s.findOrCreate(
            clickapp.ClickChronicleBenefactor)

        ticketSignup = s.findOrCreate(
            signup.FreeTicketSignup,
            benefactor=benefactor,
            prefixURL=u'signup',
            booth=booth)
        if ticketSignup.prefixURL is None:
            ticketSignup.prefixURL = signupURL
        ticketSignup.installOn(s)

        s.findOrCreate(clickapp.StaticShellContent).installOn(s)


    def installChronicleUser(self, username, domain, publicURL):
        s = self.parent.getStore()
        ls = portal.IRealm(s)

        try:
            ccAvatar = ls.addAccount(username, domain, None)
        except eaxiom.DuplicateUser:
            ccAvatar = ls.accountByAddress(username, domain)

        ccAvatarStore = ccAvatar.avatars.open()
        ccAvatarStore.findOrCreate(publicpage.ClickChroniclePublicPage).installOn(ccAvatarStore)
        ccAvatarStore.findOrCreate(clickapp.StaticShellContent).installOn(ccAvatarStore)

        for pweb in s.query(publicweb.PublicWeb, publicweb.PublicWeb.prefixURL == publicURL):
            self.log('Redirecting public at %r to ClickChronicle (was %r)' % (publicURL, pweb.application))
            pweb.application = ccAvatar
            break
        else:
            pweb = publicweb.PublicWeb(store=s, sessioned=True, prefixURL=publicURL, application=ccAvatar)
        pweb.installOn(s)


    def postOptions(self):
        if self['system-user'] is None:
            raise usage.UsageError("--system-user must be specified")
        username, domain = self.decodeCommandLine(self['system-user']).split('@')

        self.installClickChronicle(self.decodeCommandLine(self['signup-url']))
        self.installChronicleUser(username, domain, self.decodeCommandLine(self['public-url']))


class Show(usage.Options, ChronicleOptionsMixin):
    longdesc = """
    Display current ClickChronicle configuration.
    """

    def postOptions(self):
        self.didSomething = True
        s = self.parent.getStore()
        try:
            benefactor, ticketSignup = self._benefactorAndSignup()
        except eaxiom.ItemNotFound:
            print 'ClickChronicle is not installed.'
        else:
            print 'Ticket signup is at', repr(ticketSignup.prefixURL)
            print 'Max clicks is', benefactor.maxClicks

class ChroniclerConfiguration(usage.Options, axiomatic.AxiomaticSubCommandMixin, ChronicleOptionsMixin):
    classProvides(plugin.IPlugin, iaxiom.IAxiomaticCommand)

    name = 'click-chronicle-site'
    description = 'Chronicler of clicking'

    subCommands = [
        ('install', None, Install, "Install site-wide ClickChronicle components"),
        ('show', None, Show, "Show the current ClickChronicle configuration"),
        ('click-stats-interval', None, ClickStatsInterval, 'Change the interval attribute of ClickStats items'),
        ]

    def getStore(self):
        return self.parent.getStore()

    def postOptions(self):
        s = self.parent.getStore()

        def _():
            try:
                benefactor, ticketSignup = self._benefactorAndSignup()
            except eaxiom.ItemNotFound:
                raise usage.UsageError("Site-wide ClickChronicle components not yet installed.")

            if self['ticket-signup-url'] is not None:
                self.didSomething = True
                ticketSignup.prefixURL = self.decodeCommandLine(self['ticket-signup-url'])

            if self['max-clicks'] is not None:
                self.didSomething = True
                benefactor.maxClicks = int(self.decodeCommandLine(self['max-clicks']))

        s.transact(_)
        if not self.didSomething:
            self.opt_help()

from twisted.python import usage
from axiom.scripts import axiomatic
from axiom import userbase, scheduler
from sine import sipserver

class Install(axiomatic.AxiomaticSubCommand):
    "Install a SIP proxy and registrar backed by an Axiom user database."

    longdesc = __doc__

    optParameters = [
        ('port', 'p', '5060',
         'Port to listen on for SIP.'),
        ('pstn', None, '',
         'SIP URL that PSTN calls should be directed to.' ),
        ]

    def postOptions(self):
        s = self.parent.getStore()
        svc = s.findOrCreate(sipserver.SIPServer,
                             portno=int(self['port']),
                             pstn=self['pstn'])
        svc.installOn(s)

        s.findOrCreate(scheduler.Scheduler).installOn(s)
        s.findOrCreate(userbase.LoginSystem).installOn(s)


class Register(axiomatic.AxiomaticSubCommand):
    "Add an account on another host for the proxy to register with on startup."

    longdesc = __doc__
    synopsis = "<username> <domain> [password]"

    def parseArgs(self, username, domain, password=None):
        self['username'] = self.decodeCommandLine(username)
        self['domain'] = self.decodeCommandLine(domain)
        self['password'] = password

    def postOptions(self):
        s = self.parent.getStore()
        srv = s.findUnique(sipserver.SIPServer)
        if not self['username'] and self['domain']:
            raise usage.UsageError("Both a username and domain are required")
        r = sipserver.Registration(store=s,username=self['username'], password=unicode(self['password']),
                               domain=self['domain'], parent=srv)

class SIPProxyConfiguration(axiomatic.AxiomaticCommand):
    name = "sip-proxy"
    description = "SIP proxy and registrar"

    longdesc = __doc__

    subCommands = [('install', None, Install, "Install SIP Proxy components"),
                   ('register', None, Register, "Register with an external SIP registrar")
                  ]
    didSomething = False

    def getStore(self):
        return self.parent.getStore()


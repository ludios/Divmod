from nevow import tags, livepage
from axiom.attributes import text, reference
from axiom.item import Item
from xmantissa.website import PrefixURLMixin
from zope.interface import implements
from xmantissa.ixmantissa import ISiteRootPlugin
from xmantissa import signup

# workaround to put the ticket link in the page
# template itself, without changing the template file
# or the Ticket item.  a lot of copy & paste, probably
# a lot of wrongness

class EmaillessSignerUpper(signup.FreeSignerUpper):
    def handle_issueTicket(self, ctx, emailAddress):
        (domain, port) = signup.domainAndPortFromContext(ctx)
        
        if port == 80:
            port = ''
        else:
            port = ':%d' % port

        ticket = self.original.booth.createTicket(self.original,
                                                  unicode(emailAddress, 'ascii'),
                                                  self.original.benefactor)
        ticket.claim()
         
        ticketLink = 'http://%s%s/%s/%s' % (domain, port,
                                            self.original.booth.prefixURL, ticket.nonce)
        return livepage.set( 'signup-status', tags.a(href=ticketLink)['click here to redeem'] )

class EmaillessTicketSignup(Item, PrefixURLMixin):
    implements(ISiteRootPlugin)

    typeName = 'emailless_ticket_signup'
    schemaVersion = 1

    prefixURL = text()
    booth = reference()
    benefactor = reference()

    def createResource(self):
        return EmaillessSignerUpper(self)

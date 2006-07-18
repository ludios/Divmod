
from zope.interface import implements

from twisted.trial import unittest
from twisted.application import service
from twisted.mail import smtp
from twisted.internet.defer import gatherResults

from epsilon.scripts import certcreate

from axiom import store, userbase, scheduler
from axiom.item import Item, InstallableMixin
from axiom.attributes import text, reference
from axiom.test.util import getPristineStore

from xquotient import mail, exmess
from xquotient.quotientapp import QuotientBenefactor
from xquotient.compose import ComposeBenefactor
from xquotient.iquotient import IMessageSender


def createStore(testCase):
    """
    Create a database suitable for use by the L{MailTests} suite.

    @type testCase: L{MailTests}
    @rtype: L{axiom.store.Store}
    """
    location = testCase.mktemp()
    s = store.Store(location)

    def initializeStore():
        """
        Install site requirements for the MTA tests and create several users
        which will be used as the origin and destination of various test
        messages.
        """
        scheduler.Scheduler(store=s).installOn(s)
        login = userbase.LoginSystem(store=s)
        login.installOn(s)

        benefactors = [
            # XXX This is pretty broken.  ComposeBenefactor is depended on by
            # QuotientBenefactor.
            ComposeBenefactor(store=s),
            QuotientBenefactor(store=s)]

        for (localpart, domain, internal) in [
            ('testuser', 'localhost', True),
            ('testuser', 'example.com', False),
            ('administrator', 'localhost', True)]:

            account = login.addAccount(localpart, domain, None, internal=internal)
            subStore = account.avatars.open()
            def endow():
                for b in benefactors:
                    b.endow(None, subStore)
            subStore.transact(endow)
    s.transact(initializeStore)

    return s


class _DeliveryRecord(Item):
    """
    Record an attempt to deliver a message to a particular address.  Used to
    test that the correct attempts are made to send messages out of the system.
    """
    toAddress = text(doc="""
    RFC2822-format string indicating to whom this delivery would have been
    attempted.  This represents one element of the C{toAddresses} list passed
    to L{iquotient.IMessageSender.sendMessage}.
    """, default=None)

    message = reference(doc="""
    The message being delivered.
    """)

    stub = reference(doc="""
    The L{StubSender} which created this record.
    """)



class StubSender(Item, InstallableMixin):
    """
    Testable L{IMessageSender} implementation.
    """
    implements(IMessageSender)

    installedOn = reference()

    def installOn(self, other):
        super(StubSender, self).installOn(other)
        other.powerUp(self, IMessageSender)


    def sendMessage(self, toAddresses, message):
        for addr in toAddresses:
            _DeliveryRecord(store=self.store,
                            stub=self,
                            toAddress=addr,
                            message=message)


    def getSends(self):
        """
        Retrieve information about all attempts to send messages which have
        been made.

        @return: A C{list} of two-tuples of an address and a message.
        """
        return (
            (r.toAddress, r.message)
            for r
            in self.store.query(_DeliveryRecord,
                                _DeliveryRecord.stub == self))


class MailTests(unittest.TestCase):
    def setUp(self):
        self.store = getPristineStore(self, createStore)
        self.login = self.store.findUnique(userbase.LoginSystem)

        svc = service.IService(self.store)
        svc.privilegedStartService()
        svc.startService()


    def tearDown(self):
        svc = service.IService(self.store)
        return svc.stopService()


    def test_lateInstallation(self):
        """
        Test that an MTA installed on a store which has already been started
        gets started itself.
        """
        mta = mail.MailTransferAgent(store=self.store)
        mta.installOn(self.store)
        self.failUnless(mta.running)


    def test_SMTP(self):
        """
        Test that an MTA with an SMTP port number gets an IListeningPort for
        cleartext communication when it is started.
        """
        mta = mail.MailTransferAgent(store=self.store)
        mta.installOn(self.store)

        self.failIfEqual(mta.port, None)
        self.assertEquals(mta.securePort, None)


    def test_SMTPS(self):
        """
        Test that an MTA with an SMTP/SSL port number and a certificate gets an
        IListeningPort for encrypted communication when it is started.
        """
        certfile = self.mktemp()
        certcreate.main(['--filename', certfile])

        mta = mail.MailTransferAgent(store=self.store,
                                     portNumber=None,
                                     securePortNumber=0,
                                     certificateFile=certfile)
        mta.installOn(self.store)

        self.assertEqual(mta.port, None)
        self.failIfEqual(mta.securePort, None)


    def test_messageTransferAgentDeliveryFactory(self):
        """
        Test that L{mail.MailTransferAgent} properly powers up the Item it is
        installed on for L{smtp.IMessageDeliveryFactory} and that the
        L{smtp.IMessageDelivery} provider it makes available is at least
        minimally functional.
        """
        mta = mail.MailTransferAgent(store=self.store)
        mta.installOn(self.store)
        factory = smtp.IMessageDeliveryFactory(self.store)
        delivery = factory.getMessageDelivery()
        self.failUnless(smtp.IMessageDelivery.providedBy(delivery))


    def test_messageDeliveryAgentDeliveryFactory(self):
        """
        Similar to L{test_messageTransferAgentDeliveryFactory}, but test
        L{mail.MailDeliveryAgent} instead.
        """
        account = self.login.accountByAddress(u'testuser', u'example.com')
        factory = smtp.IMessageDeliveryFactory(account)
        delivery = factory.getMessageDelivery()
        self.failUnless(smtp.IMessageDelivery.providedBy(delivery))


    def test_validateFromUnauthenticatedLocal(self):
        """
        Test that using a local address as the sender address without
        authenticating as that user raises an exception to prevent the
        delivery.
        """
        factory = mail.MailTransferAgent(store=self.store)
        factory.installOn(self.store)
        delivery = factory.getMessageDelivery()
        d = delivery.validateFrom(
            ('home.example.net', '192.168.1.1'),
            smtp.Address('testuser@localhost'))
        return self.assertFailure(d, smtp.SMTPBadSender)


    def test_validateFromUnauthenticatedNonLocal(self):
        """
        Test that using a non-local address as the sender address without
        authenticating first is accepted.
        """
        factory = mail.MailTransferAgent(store=self.store)
        factory.installOn(self.store)
        delivery = factory.getMessageDelivery()

        addr = smtp.Address('testuser@example.com')
        d = delivery.validateFrom(('home.example.net', '192.168.1.1'), addr)
        return d.addCallback(self.assertEquals, addr)


    def test_validateFromAuthenticatedLocal(self):
        """
        Test that using a local address as the sender address after
        authenticating as the user who owns that address is accepted.
        """
        avatar = self.login.accountByAddress(u'testuser', u'localhost')
        delivery = smtp.IMessageDeliveryFactory(avatar).getMessageDelivery()

        addr = smtp.Address('testuser@localhost')
        d = delivery.validateFrom(('home.example.net', '192.168.1.1'), addr)
        return d.addCallback(self.assertEquals, addr)


    def test_validateFromAuthenticatedDisallowedLocal(self):
        """
        Test that using a local address as the sender address after
        authenticating as a user who does /not/ own that address is rejected.
        """
        avatar = self.login.accountByAddress(u'testuser', u'localhost')
        delivery = smtp.IMessageDeliveryFactory(avatar).getMessageDelivery()

        addr = smtp.Address('admistrator@localhost')
        d = delivery.validateFrom(('home.example.net', '192.168.1.1'), addr)
        return self.assertFailure(d, smtp.SMTPBadSender)


    def test_validateFromAuthenticatedNonLocal(self):
        """
        Test that using a non-local address as the sender address after
        authenticating as a user is rejected.
        """
        avatar = self.login.accountByAddress(u'testuser', u'localhost')
        delivery = smtp.IMessageDeliveryFactory(avatar).getMessageDelivery()

        addr = smtp.Address('testuser@example.com')
        d = delivery.validateFrom(('home.example.net', '192.168.1.1'), addr)
        return self.assertFailure(d, smtp.SMTPBadSender)


    def test_validateToUnauthenticatedLocal(self):
        """
        Test that using a local address as the recipient address without
        authenticating is accepted.
        """
        factory = mail.MailTransferAgent(store=self.store)
        factory.installOn(self.store)
        delivery = factory.getMessageDelivery()

        addr = smtp.Address('someone.else@example.com')
        d = delivery.validateFrom(('home.example.net', '192.168.1.1'), addr)
        def validatedFrom(ign):
            d = delivery.validateTo(
                smtp.User(
                    smtp.Address('testuser', 'localhost'),
                    None, None, None))
            return d
        d.addCallback(validatedFrom)
        return d


    def test_validateToUnauthenticatedNonLocal(self):
        """
        Test that using a non-local address as the recipient address without
        authenticating is rejected.
        """
        factory = mail.MailTransferAgent(store=self.store)
        factory.installOn(self.store)
        delivery = factory.getMessageDelivery()

        addr = smtp.Address('someone.else@example.com')
        d = delivery.validateFrom(('home.example.net', '192.168.1.1'), addr)
        def validatedFrom(ign):
            d = delivery.validateTo(
                smtp.User(
                    smtp.Address('another.user@example.net'),
                    None, None, None))
            return self.assertFailure(d, smtp.SMTPBadRcpt)
        d.addCallback(validatedFrom)
        return d


    def test_validateToUnauthenticatedNonExistentLocal(self):
        """
        Test that using as the recipient address a non-existent address which
        would exist locally if it existed at all is rejected.
        """
        factory = mail.MailTransferAgent(store=self.store)
        factory.installOn(self.store)
        delivery = factory.getMessageDelivery()

        addr = smtp.Address('someone.else@example.com')
        d = delivery.validateFrom(('home.example.net', '192.168.1.1'), addr)
        def validatedFrom(ign):
            d = delivery.validateTo(
                smtp.User(
                    smtp.Address('nonexistent', 'localhost'),
                    None, None, None))
            return self.assertFailure(d, smtp.SMTPBadRcpt)
        d.addCallback(validatedFrom)
        return d


    def test_validateToAuthenticatedLocal(self):
        """
        Test that using a local address as the recipient address after
        authenticating as anyone is accepted.
        """
        avatar = self.login.accountByAddress(u'testuser', u'localhost')
        delivery = smtp.IMessageDeliveryFactory(avatar).getMessageDelivery()

        addr = smtp.Address('testuser@localhost')
        d = delivery.validateFrom(('home.example.net', '192.168.1.1'), addr)
        def validatedFrom(ign):
            d = delivery.validateTo(
                smtp.User(
                    smtp.Address('administrator', 'localhost'),
                    None, None, None))
            return d
        d.addCallback(validatedFrom)
        return d


    def test_validateToAuthenticatedNonLocal(self):
        """
        Test that using a non-local address as the recipient address after
        authenticating as anyone is accepted.
        """
        avatar = self.login.accountByAddress(u'testuser', u'localhost')
        delivery = smtp.IMessageDeliveryFactory(avatar).getMessageDelivery()

        addr = smtp.Address('testuser@localhost')
        d = delivery.validateFrom(('home.example.net', '192.168.1.1'), addr)
        def validatedFrom(ign):
            d = delivery.validateTo(
                smtp.User(
                    smtp.Address('administrator', 'example.com'),
                    None, None, None))
            return d
        d.addCallback(validatedFrom)
        return d


    def test_validateToAuthenticatedNonExistentLocal(self):
        """
        Test that using as the recipient address a non-existent address which
        would exist locally if it existed at all is rejected.
        """
        avatar = self.login.accountByAddress(u'testuser', u'localhost')
        delivery = smtp.IMessageDeliveryFactory(avatar).getMessageDelivery()

        addr = smtp.Address('testuser@localhost')
        d = delivery.validateFrom(('home.example.net', '192.168.1.1'), addr)
        def validatedFrom(ign):
            d = delivery.validateTo(
                smtp.User(
                    smtp.Address('nonexistent', 'localhost'),
                    None, None, None))
            return self.assertFailure(d, smtp.SMTPBadRcpt)
        d.addCallback(validatedFrom)
        return d


    def deliverMessageAndVerify(self, messageFactory, recipientLocal, recipientDomain):
        """
        L{deliver} then L{verify}.
        """
        self.deliver(messageFactory)
        self.verify(recipientLocal, recipientDomain)


    def deliver(self, messageFactory):
        """
        Create a message using the given factory and deliver a message to it.
        """
        if isinstance(messageFactory, list):
            map(self.deliver, messageFactory)
        else:
            msg = messageFactory()
            msg.lineReceived('Header: value')
            msg.lineReceived('')
            msg.lineReceived('Goodbye.')
            msg.eomReceived()


    def verify(self, recipientLocal, recipientDomain):
        """
        Assert that the message has made it into the database of the given user
        as an L{exmess.Message} instance.
        """
        account = self.login.accountByAddress(recipientLocal, recipientDomain)
        avatar = account.avatars.open()
        messages = list(avatar.query(exmess.Message,
                                     exmess.Message.outgoing == False))
        self.assertEquals(len(messages), 1)
        self.assertIn(
            'Goodbye.',
            messages[0].impl.source.open().read())


    def test_unauthenticatedMailDelivery(self):
        """
        Test that an unauthenticated user sending mail to a local user actually
        gets his message delivered.
        """
        d = self.test_validateToUnauthenticatedLocal()
        d.addCallback(self.deliverMessageAndVerify, u'testuser', u'localhost')
        return d


    def verifyOutgoing(self, sender, localpart, domain):
        """
        Assert that there is a message scheduled to be delivered to the given
        address.
        """
        address = u'@'.join((localpart, domain))
        for (toAddr, msg) in sender.getSends():
            if toAddr == address:
                return
        self.fail("No message addressed to %r" % (address,))


    def test_authenticatedMailDelivery(self):
        """
        Test that an authenticated user sending mail to a local user actually
        gets his message delivered and gets a record of that message in the
        form of a sent message.
        """
        sender = self.installStubSender(u'testuser', u'localhost')
        d = self.test_validateToAuthenticatedLocal()
        d.addCallback(self.deliver)
        def verify(ign):
            # This works even though outgoing *should* be True on this message
            # because apparently it is Composer's responsibility to set that
            # flag, and Composer isn't being allowed to run here.
            self.verify(u'testuser', u'localhost')
            return self.verifyOutgoing(
                sender, u'administrator', u'localhost')
        d.addCallback(verify)
        return d


    def installStubSender(self, localpart, domain):
        """
        Replace the IMessageSender powerup on the named avatar with a testable
        implementation.

        @rtype: L{StubMessage}
        """
        # Remove the real IMessageSender so it doesn't try to actually deliver
        # any mail.
        account = self.login.accountByAddress(localpart, domain)
        avatar = account.avatars.open()
        sender = IMessageSender(account)
        avatar.powerDown(sender, IMessageSender)

        # Put in a new stub IMessageSender which we can use to assert things
        # about the sending behavior in this case.
        newSender = StubSender(store=avatar)
        newSender.installOn(avatar)
        return newSender


    def test_authenticatedMailTransfer(self):
        """
        Test that an authenticated user sending mail to a remote user actually
        gets his message delivered and gets a record of the transmission in the
        form of a sent message object.
        """
        sender = self.installStubSender(u'testuser', u'localhost')
        d = self.test_validateToAuthenticatedNonLocal()
        d.addCallback(self.deliver)
        def verify(ign):
            # This works even though outgoing *should* be True on this message
            # because apparently it is Composer's responsibility to set that
            # flag, and Composer isn't being allowed to run here.
            self.verify(u'testuser', u'localhost')
            self.verifyOutgoing(
                sender, u'administrator', u'example.com')
        d.addCallback(verify)
        return d


    MULTI_RECIPIENT_ADDRESSES = [
        'alice@example.com',
        'bob@example.com',
        'carol@example.com']


    def test_authenticatedMultipleRecipientsOneRecord(self):
        """
        Test that only one sent message object is created even if a messages is
        destined for multiple recipients.
        """
        sender = self.installStubSender(u'testuser', u'localhost')
        account = self.login.accountByAddress(u'testuser', u'localhost')
        factory = smtp.IMessageDeliveryFactory(account)
        delivery = factory.getMessageDelivery()

        d = delivery.validateFrom(
            ('home.example.net', '192.168.1.1'),
            smtp.Address('testuser@localhost'))
        def validatedFrom(ign):
            return gatherResults([
                    delivery.validateTo(
                        smtp.User(
                            smtp.Address(addr), None, None, None))
                    for addr in self.MULTI_RECIPIENT_ADDRESSES])
        d.addCallback(validatedFrom)
        d.addCallback(self.deliverMessageAndVerify, u'testuser', u'localhost')
        return d


    def test_authenticatedMultipleRecipientsDelivery(self):
        """
        Test that each local recipient to whom a message is addressed receives
        a copy of the message.
        """
        d = self.test_authenticatedMultipleRecipientsOneRecord()
        account = self.login.accountByAddress(u'testuser', u'localhost')
        sender = IMessageSender(account)
        def verifySends(ign):
            for addr in self.MULTI_RECIPIENT_ADDRESSES:
                self.verifyOutgoing(sender, *addr.split(u'@'))
        d.addCallback(verifySends)
        return d


    def test_authenticatedReceivedHeader(self):
        """
        Test that something at least minimally reasonable comes back from the
        receivedHeader method of L{AuthenticatedMessageDelivery}.
        """
        avatar = self.login.accountByAddress(u'testuser', u'localhost')
        composer = IMessageSender(avatar)

        delivery = mail.AuthenticatedMessageDelivery(composer.store, composer)
        header = delivery.receivedHeader(
            ("example.com", "192.168.123.45"),
            smtp.Address("testuser@localhost"),
            [smtp.User("recip@example.net", None, None, None),
             smtp.User("admin@example.org", None, None, None)])

        self.failUnless(
            isinstance(header, str),
            "Got %r instead of a string" % (header,))


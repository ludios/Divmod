# -*- test-case-name: xquotient.test -*-

from zope.interface import Interface

class IMIMEDelivery(Interface):
    def createMIMEReceiver():
        """Create an object to accept a MIME message.

        @rtype: L{twisted.mail.smtp.IMessage}
        """
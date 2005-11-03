from sine.test.test_sip import FakeClockTestCase, TestRealm, PermissiveChecker
from sine import sip
from shtoom.rtp.protocol import RTPProtocol
from twisted import cred
from twisted.internet import reactor
from twisted.trial import unittest

exampleInvite = """INVITE sip:bob@proxy2.org SIP/2.0\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9\r
Max-Forwards: 70\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 INVITE\r
Contact: <sip:alice@client.com>\r
\r
v=0\r
o=alice 2890844526 2890844526 IN IP4 server.com\r
s=-\r
c=IN IP4 10.0.0.1\r
t=0 0\r
m=audio 49172 RTP/AVP 0\r
a=rtpmap:0 PCMU/8000\r
"""


response180 = """\
SIP/2.0 180 Ringing\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74bf9;received=10.0.0.1;received=10.0.0.1\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>;tag=314159\r
Call-ID: 3848276298220188511@client.com\r
Contact: <sip:bob@server.com>\r
CSeq: 1 INVITE\r
\r
"""

response200 = """SIP/2.0 200 OK\r
Via: SIP/2.0/UDP client.com:1234;branch=z9hG4bK74bf9;received=10.0.0.1\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>;tag=314159\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 INVITE\r
User-Agent: Divmod Sine\r
Content-Length: 125\r
Content-Type: application/sdp\r
Contact: sip:jethro@example.com\r
\r
v=0\r
o=bob 2890 2890121 IN IP4 127.0.0.2\r
s=shtoom\r
c=IN IP4 127.0.0.2\r
t=0 0\r
m=audio 3456 RTP/AVP 0\r
a=rtpmap:0 PCMU/8000\r
"""

ackRequest = """\
ACK sip:bob@proxy2.org SIP/2.0\r
Via: SIP/2.0/UDP client.com:5060;branch=z9hG4bK74b76\r
Max-Forwards: 70\r
Route: sip:proxy2.org:5060;lr\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
To: Bob <sip:bob@proxy2.org>;tag=314159\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 ACK\r
\r
"""

byeRequest = """\
BYE sip:bob@proxy2.org SIP/2.0\r
Via: SIP/2.0/UDP server.com:5060;branch=z9hG4bKnashds7\r
Max-Forwards: 70\r
To: Bob <sip:bob@proxy2.org>;tag=314159\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
Call-ID: 3848276298220188511@client.com\r
CSeq: 1 BYE\r
\r
"""

byeResponse = """\
SIP/2.0 200 OK\r
Via: SIP/2.0/UDP server.com:5060;branch=z9hG4bKnashds7;received=10.0.0.2\r
To: Bob <sip:bob@proxy2.org>;tag=314159\r
From: Alice <sip:alice@proxy1.org>;tag=9fxced76sl\r
Call-ID: 3848276298220188511@client.com\r
User-Agent: Divmod Sine\r
CSeq: 1 BYE\r
Content-Length: 0\r
\r
"""
#XXX


class CallTerminateTest(FakeClockTestCase):

    def setUp(self):
        r = TestRealm("server.com")
        p = cred.portal.Portal(r)
        p.registerChecker(PermissiveChecker())
        fakeRTP = RTPProtocol(None, "")
        fakeRTP._extIP = "127.0.0.2"
        fakeRTP._extRTPPort = 8000
        self.uas = sip.SimpleCallAcceptor(fakeRTP,
                                          sip.parseURL("sip:bob@proxy2.org"))
        self.sent = []
        self.sip = sip.SIPTransport(self.uas, ["server.com"], 5060)
        self.sip.sendMessage = lambda dest, msg: self.sent.append((dest, msg))
        self.testMessages = []
        self.parser = sip.MessagesParser(self.testMessages.append)

        #XXX this is probably not good
        sip.Dialog.genTag = lambda self: "314159"

    def tearDown(self):
        self.clock.advance(33)
        reactor.iterate()
        self.clock.advance(33)
        reactor.iterate()

    def assertMsgEqual(self, first, second):
        self.testMessages[:] = []
        if isinstance(first, basestring):
            self.parser.dataReceived(first)
            self.parser.dataDone()
        else:
            #presumably a Message
            self.testMessages.append(first)
        if isinstance(second, basestring):
            self.parser.dataReceived(second)
            self.parser.dataDone()
        else:
            self.testMessages.append(second)
        self.fuzzyMatch(self.testMessages[0],  self.testMessages[1])

    def fuzzyMatch(self, first, second):
        "try to ignore bits randomly generated by our code"
        self.assertEqual(first.__class__, second.__class__)
        self.assertEqual(first.version, second.version)
        if isinstance(first, sip.Request):
            self.assertEqual(first.method, second.method)
            self.assertEqual(first.uri, second.uri)
        else:
            self.assertEqual(first.code, second.code)

        for header in first.headers.keys():
            if not second.headers.get(header):
                if not first.headers[header]:
                    #woops, it's empty, never mind
                    continue
                raise unittest.FailTest("%s not present in %s" % (header, second))
            if header in ('from', 'to', 'contact'):
                #strip tags
                if isinstance(first.headers[header][0], sip.URL):
                    firsturl = first.headers[header][0]
                else:
                    firsturl = sip.parseAddress(first.headers[header][0])[1]
                secondurl = sip.parseAddress(second.headers[header][0])[1]
                self.assertEqual(firsturl, secondurl)
            elif header == "via":
                firstvia = [sip.parseViaHeader(h)
                            for h in first.headers['via']]
                secondvia = [sip.parseViaHeader(h)
                            for h in second.headers['via']]
                #convert to strings for easy reading of output
                self.assertEqual([x.toString() for x in firstvia],
                                 [x.toString() for x in firstvia])
            else:
                self.assertEqual([str(x) for x in first.headers[header]],
                                 [str(x) for x in second.headers[header]])
    def testCallTermination(self):
        self.sip.datagramReceived(exampleInvite, ('10.0.0.1', 5060))
        reactor.iterate()
        self.assertEquals(len(self.sent), 1)
        self.assertMsgEqual(self.sent[0][0], response200)
        self.sent = []

        
        self.sip.datagramReceived(ackRequest, ('10.0.0.1', 5060))
        self.assertEquals(len(self.sent), 0)
        self.sip.datagramReceived(byeRequest, ('10.0.0.1', 5060))
        self.assertEquals(len(self.sent), 1)
        self.assertMsgEqual(self.sent[0][0], byeResponse)


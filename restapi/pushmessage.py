from struct import pack
from OpenSSL import SSL
import struct
from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory, Protocol
from twisted.internet.ssl import ClientContextFactory

APNS_SERVER_HOSTNAME = "gateway.sandbox.push.apple.com"
APNS_SERVER_PORT = 2195
APNS_SSL_CERTIFICATE_FILE = "<your ssl certificate.pem>"
APNS_SSL_PRIVATE_KEY_FILE = "<your ssl private key.pem>"

class APNSClientContextFactory(ClientContextFactory):
    def __init__(self):
        self.ctx = SSL.Context(SSL.SSLv3_METHOD)
        self.ctx.use_certificate_file(APNS_SSL_CERTIFICATE_FILE)
        self.ctx.use_privatekey_file(APNS_SSL_PRIVATE_KEY_FILE)

    def getContext(self):
        return self.ctx

class APNSProtocol(Protocol):
    def sendMessage(self, deviceToken, payload):
        # notification messages are binary messages in network order
        # using the following format:
        # <1 byte command> <2 bytes length><token> <2 bytes length><payload>
        fmt = "!cH32cH%dc" % len(payload)
        command = 0
        msg = struct.pack(fmt, command, deviceToken,
                          len(payload), payload)
        self.transport.write(msg)

class APNSClientFactory(ClientFactory):
    def buildProtocol(self, addr):
		EventLog().add_event(
	        body='',
	        where='pushmessage.APNSClientFactory.buildProtocol, line=37')
        return APNSProtocol()

    def clientConnectionLost(self, connector, reason):
		EventLog().add_event(
	        body='',
	        where='pushmessage.APNSClientFactory.clientConnectionLost, line=43')

    def clientConnectionFailed(self, connector, reason):
		EventLog().add_event(
	        body='',
	        where='pushmessage.APNSClientFactory.clientConnectionFailed, line=48')

if __name__ == '__main__':
    reactor.connectSSL(APNS_SERVER_HOSTNAME, 
                       APNS_SERVER_PORT,
                       APNSClientFactory(), 
                       APNSClientContextFactory())
    reactor.run()
    APNSProtocol.sendMessage(self,)
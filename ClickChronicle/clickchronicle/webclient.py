
"""
Cheesy web client functions to do things that twisted.web.client can't
do.
"""

from twisted.web import client
from twisted.internet import reactor

def getPage(url, contextFactory=None, *args, **kwargs):
    """Download a web page as a string.

    Download a page. Return a deferred, which will callback with a
    page (as a string) or errback with a description of the error.

    See HTTPClientFactory to see what extra args can be passed.
    """
    scheme, host, port, path = client._parse(url)
    factory = client.HTTPClientFactory(url, *args, **kwargs)
    if scheme == 'https':
        from twisted.internet import ssl
        if contextFactory is None:
            contextFactory = ssl.ClientContextFactory()
        reactor.connectSSL(host, port, factory, contextFactory)
    else:
        reactor.connectTCP(host, port, factory)
    return factory

def getPageAndHeaders(headers, *a, **kw):
    f = getPage(*a, **kw)

    def gotPage(page):
        return (page, [f.response_headers.get(h, []) for h in headers])

    return f.deferred.addCallback(gotPage)

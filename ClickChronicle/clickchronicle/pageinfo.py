from BeautifulSoup import BeautifulSoup
import re

def lowerValues(tags, keys):
    for attrs in tags:
        for key in keys:
            value = attrs.get(key)
            if value is not None:
                attrs[key] = value.lower()

def mergeDefaults(results, defaults):
    for (k, defv) in defaults.iteritems():
        if results[k] is None:
            results[k] = defv

class DoneParsing(Exception):
    """
       strange things seem to happen to sgmllib if reset() is called
       in a start_ handler - making it difficult for us to stop parsing
       dead in our tracks - so we'll use exception to communicate results
       to the user of PageInfoParser
    """

class PageInfoParser(BeautifulSoup):
    charsetRegex = re.compile(r";\s*charset=(\S+)$")
    headTags = ("script", "noscript", "link", "meta", "title")
    seenHead = False

    def __init__(self, html, defaults):
        self.metaTags = []
        self.linkTags = []
        self.title = None
        self.defaults = defaults
        BeautifulSoup.__init__(self, html)

    def abort(self, t=None):
        raise DoneParsing, self.pageInfo(**self.defaults)

    def do_head(self, tag):
        self.seenHead = True

    def unknown_starttag(self, tag, attributes):
        if self.seenHead and tag not in self.headTags:
            self.abort()
        BeautifulSoup.unknown_starttag(self, tag, attributes)

    def do_link(self, attrs):
        self.linkTags.append(dict(attrs))

    def do_meta(self, attrs):
        self.metaTags.append(dict(attrs))

    def handle_data(self, data):
        if self.currentTag.name == "title" and self.title is None:
            self.title = data
        BeautifulSoup.handle_data(self, data)

    def getCharset(self):
        for ctype in (d.get("content") for d in self.metaTags
                        if d.get("http-equiv") == "content-type"):

            match = self.charsetRegex.search(ctype)
            if match is not None:
                return match.group(1)

    def getFaviconURL(self):
        for faviconURL in (d.get("href") for d in self.linkTags
                            if d.get("rel") == "icon"):
            return faviconURL

    def pageInfo(self, **defaults):
        lowerValues(self.linkTags, ("rel",))
        lowerValues(self.metaTags, ("http-equiv",))

        # if we were supplied default values for title, charset, or faviconURL,
        # and didn't get data from the page source for any of those fields,
        # substitute defaults

        refutableResults = dict(title=self.title,
                                charset=self.getCharset(),
                                faviconURL=self.getFaviconURL())

        mergeDefaults(refutableResults, defaults)

        return PageInfo(self.metaTags, self.linkTags, **refutableResults)

class PageInfo(object):
    __slots__ = ("title", "charset", "faviconURL", "metaTags", "linkTags")

    def __init__(self, metaTags, linkTags, faviconURL=None, title=None, charset=None):
        self.charset = charset
        self.faviconURL = faviconURL
        self.metaTags = metaTags
        self.title = title
        self.linkTags = linkTags

def getPageInfo(html, **defaults):
    try:
        p = PageInfoParser(html, defaults)
    except DoneParsing, dp:
        (pageInfo,) = dp.args
        return pageInfo
    else:
        return p.pageInfo(**defaults)

if __name__ == "__main__":
    import sys
    pinfo = getPageInfo(file(sys.argv[1]).read())
    print "Charset: ", pinfo.charset
    print "Favicon URL:", pinfo.faviconURL
    print "Meta Tags:", pinfo.metaTags
    print "Title:", pinfo.title
    print "Link Tags:", pinfo.linkTags

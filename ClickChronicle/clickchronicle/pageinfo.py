from BeautifulSoup import BeautifulSoup
import re

class PageInfoParser(BeautifulSoup):
    charsetRegex = re.compile(r";\s*charset=(\S+)$")
    
    def __init__(self, *a, **k):
        self.metaTags = []
        self.linkTags = []
        self.title = None
        BeautifulSoup.__init__(self, *a, **k)

    end_head = start_body = lambda self, tag: self.reset()
    parse_comment = lambda self, tag: None

    def do_link(self, attrs):
        self.linkTags.append(dict(attrs)) 

    def do_meta(self, attrs):
        self.metaTags.append(dict(attrs))

    def handle_data(self, data):
        if self.currentTag.name == "title" and self.title is None:
            self.title = data

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
        
    def lowerValues(self, tags, keys):
        for attrs in tags:
            for key in keys:
                value = attrs.get(key)
                if value is not None:
                    attrs[key] = value.lower()
                    
    def pageInfo(self):
        self.lowerValues(self.linkTags, ("rel",))
        self.lowerValues(self.metaTags, ("http-equiv",))
        return PageInfo(self.title, self.getCharset(), self.getFaviconURL(),
                        self.metaTags, self.linkTags)
                        
class PageInfo(object):
    __slots__ = ("title", "charset", "faviconURL", "metaTags", "linkTags")

    def __init__(self, title, charset, faviconURL, metaTags, linkTags):
        self.charset = charset
        self.faviconURL = faviconURL
        self.metaTags = metaTags
        self.title = title
        self.linkTags = linkTags 

getPageInfo = lambda html: PageInfoParser(html).pageInfo()

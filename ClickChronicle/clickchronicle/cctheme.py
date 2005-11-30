from xmantissa import webtheme
from nevow import tags

class ClickChronicleTheme(webtheme.XHTMLDirectoryTheme):
    def head(self):
        yield tags.link(rel="stylesheet", type="text/css",
                        href="/ClickChronicle/static/css/clickchronicle.css")
        yield tags.link(rel="icon", type="image/png",
                        href="/ClickChronicle/static/images/favicon.png")

from xmantissa import webtheme
from nevow import tags

class ClickChronicleTheme(webtheme.XHTMLDirectoryTheme):
    def head(self, website):
        root = website.cleartextRoot()
        yield tags.link(
            rel="stylesheet",
            type="text/css",
            href=root + "/ClickChronicle/static/css/clickchronicle.css")
        yield tags.link(
            rel="icon",
            type="image/png",
            href=root + "/ClickChronicle/static/images/favicon.png")

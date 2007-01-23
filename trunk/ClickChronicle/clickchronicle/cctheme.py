# -*- test-case-name: clickchronicle.test.test_theme -*-
from xmantissa import webtheme
from nevow import tags

class ClickChronicleTheme(webtheme.XHTMLDirectoryTheme):
    def head(self, req, website):
        root = website.cleartextRoot(req.getHeader('host'))
        static = root.child('ClickChronicle').child('static')
        yield tags.link(
            rel="stylesheet",
            type="text/css",
            href=static.child('css').child('clickchronicle.css'))
        yield tags.link(
            rel="icon",
            type="image/png",
            href=static.child('images').child('favicon.png'))

from clickchronicle.pageinfo import getPageInfo
from twisted.trial.unittest import TestCase

goodHtml = """
<html>
    <head>
        <title>%(title)s</title>
        <link rel="icon" href="%(faviconURL)s" />
        <meta http-equiv="content-type" content="text/html; charset=%(charset)s" />
    </head>
    <body>this is a bland body</body>
</html>
"""

notSoGoodHtml = """
<title>%(title)s</title>
<link rel="ICON" href="%(faviconURL)s" />
<meta HTTP-EQUIV="content-Type" content="text/html; charset=%(charset)s" />
<body>
    <link rel=ICON href="%(faviconURL2)s />
"""

class PageInfoTestCase(TestCase):
    def testWellFormed(self):
        data = dict(faviconURL="/a/favicon.ico", title="some title", charset="ISO-2022-JP")
        info = getPageInfo(goodHtml % data)
        self.assertEqual(info.title, data["title"])
        self.assertEqual(info.charset, data["charset"])
        self.assertEqual(info.faviconURL, data["faviconURL"])

    def testMalformed(self):
        data = dict(faviconURL="blah.png", title="TITLE!@!",
                    charset="abcdefg", faviconURL2="ignore.png")

        info = getPageInfo(notSoGoodHtml % data)
        self.assertEqual(info.title, data["title"])
        self.assertEqual(info.charset, data["charset"])
        self.assertEqual(info.faviconURL, data["faviconURL"])

        try:
            (linkTag,) = info.linkTags
        except ValueError:
            self.fail("expected only one link tag")

        self.assertEqual(linkTag["href"], data["faviconURL"])

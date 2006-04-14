import re

from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup

def _massageMicrosoftBytes(match):
    char = match.group(1)
    if isinstance(char, unicode):
        char = char.encode('charmap')
    return '&' + BeautifulStoneSoup.MS_CHARS[char] + ';'

BeautifulStoneSoup.PARSER_MASSAGE[-1] = (
    re.compile("([\x80-\x9f])", re.M),
    _massageMicrosoftBytes)



class Minestrone(BeautifulSoup):
    """
    i callback a given function with the node value each time i
    find a new text node.  i ignore text nodes whose immediate
    parent tag-name is inside self.ignoreTags
    """
    ignoreTags = ['script', 'style']

    def __init__(self, html, onData, **k):
        self.onData = onData
        BeautifulSoup.__init__(self, html, **k)

    noOp = lambda self, data: None
    # beautiful soup forwards this nonsense to handle_data by default
    handle_pi = handle_comment = handle_charref = handle_entityref = handle_decl = noOp

    def handle_data(self, data):
        if self.currentTag.name not in self.ignoreTags:
            self.onData(data)
        BeautifulSoup.handle_data(self, data)

class OxTail(Minestrone):
    """i accumulate text node data"""

    def __init__(self, html):
        self.textNodes = []
        Minestrone.__init__(self, html, self.textNodes.append)

    def handle_data(self, data):
        if not data.isspace():
            return Minestrone.handle_data(self, data)

    def results(self):
        return ' '.join(self.textNodes)

cook = lambda html: OxTail(html).results()

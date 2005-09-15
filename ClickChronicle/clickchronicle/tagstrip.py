from BeautifulSoup import BeautifulSoup

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

    def handle_data(self, data):
        if self.currentTag.name not in self.ignoreTags:
            self.onData(data)
        BeautifulSoup.handle_data(self, data)

def stripTags(html):
    """be friendly and accumulate the results of Minestrone's callback"""

    texts = []
    soup = Minestrone(html, texts.append)
    return ' '.join(texts)

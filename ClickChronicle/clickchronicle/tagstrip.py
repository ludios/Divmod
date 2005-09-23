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

    noOp = lambda self, data: None
    # beautiful soup forwards this nonsense to handle_data by default
    handle_pi = handle_comment = handle_charref = handle_entityref = handle_decl = noOp

    def handle_data(self, data):
        if self.currentTag.name not in self.ignoreTags:
            self.onData(data)
        BeautifulSoup.handle_data(self, data)

class OxTail(Minestrone):
    """i accumulate <meta> tags, and text nodes"""

    def __init__(self, html):
        self.textNodes = []
        self.metaTags = {}
        Minestrone.__init__(self, html, self.textNodes.append)

    def do_meta(self, attrs):
        attrs = dict(attrs)
        # XXX - Not pretty! Depends on there only being 2 keys in attrs
        # one of which is content. Returns dict of dicts. First dict key
        # is the word immediately after META e.g. 'http-equiv' or name.
        # The key of the nested dict is the value of the first key and
        # the value at the nested dict is the content.
        if 'content' in attrs:
            content = attrs.pop('content')
            key, value = attrs.popitem()
            thisDict = self.metaTags.setdefault(key, {})
            thisDict[value]=content
#        if 'name' in attrs and 'content' in attrs:
#            values = self.metaTags.setdefault(attrs['name'], [])
#            values.append(attrs['content'])

    def handle_data(self, data):
        if not data.isspace():
            return Minestrone.handle_data(self, data)

    def results(self):
        return (' '.join(self.textNodes), self.metaTags)

cook = lambda html: OxTail(html).results()

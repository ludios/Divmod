       
# extract meta tags from a HTML document
# (based on sgmllib-example-1 in the effbot guide)
# START COPY - Copied from http://mail.python.org/pipermail/python-list/2001-January/023700.html

import sgmllib

class ExtractMeta(sgmllib.SGMLParser):

    def __init__(self, verbose=0):
        sgmllib.SGMLParser.__init__(self, verbose)
        self.meta = []
        
    def do_meta(self, attrs):
        name = content = None
        for k, v in attrs:
            if k == "name":
                name = v
            if k == "content":
                content = v
        if name and content:
            self.meta.append((name, content))
                            
    def end_title(self):
        # ignore meta tags after </title>.  you
        # can comment away this method if you
        # want to parse the entire file
        raise EOFError
    
def getMeta(source):
    """
    Extract meta tags from an HTML doc.
    """
    p = ExtractMeta()
    try:
        p.feed(source)
    except EOFError:
        pass
    return p.meta

# END COPYING

from twisted.web import microdom, domhelpers, client
def getPageSource(url):
    """Asynchronously get the page source for a URL.
    """
        
    return client.getPage(url)    

import re
rawstr = r"""<.*?>"""
compiled_re = re.compile(rawstr,  re.IGNORECASE| re.DOTALL)

def getText(source):
    """
    Get all the text from an HTML doc.
    """
    #doc = microdom.parseString(source, beExtremelyLenient=True)
    #text = domhelpers.gatherTextNodes(doc)
    text = compiled_re.subn(' ', source)[0]
    return text


from xapwrap.xapwrap import Document, TextField, SortKey, Keyword                                                                        
def makeDoc(visit, pageSource):
    keywords = [
        Keyword('type', 'url'),
        Keyword('url', visit.url),
        Keyword('title', visit.title)]
    metaDict = getMeta(pageSource)
    text = getText(pageSource)
    textFields = [TextField(text)]
    for k, v in metaDict:
        textFields.append(TextField(v))
    # XXX - Not sure how xapwrap handles multiple text fields
    # Use storeID for possibly simpler removal of visit from index at a later stage
    doc = Document(uid=visit.storeID, textFields=textFields, keywords=keywords)
    return doc
    

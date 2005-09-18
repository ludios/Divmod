import os

from zope.interface import implements

from axiom.item import Item
from axiom import attributes

from clickchronicle import indexinghelp

class Domain(Item):
    url = attributes.bytes()
    title = attributes.bytes()
    visitCount = attributes.integer(default=0)
    ignore = attributes.integer(default=0) # Boolean

    schemaVersion = 1
    typeName = 'domain'

class Visit(Item):
    """I correspond to a webpage-visit logged by a clickchronicle user"""
    implements(indexinghelp.IIndexable)
    timestamp = attributes.timestamp()
    url = attributes.bytes()
    title = attributes.bytes()
    visitCount = attributes.integer(default=0)
    domain = attributes.reference(allowNone = False)
    referrer = attributes.reference(allowNone=True)

    schemaVersion = 1
    typeName = 'visit'

    def asDocument(self):
        """
        Return a Document in a Deferred.
        """
        def cbGotSource(pageSource):
            doc = indexinghelp.makeDocument(self, pageSource)
            return doc
        d = indexinghelp.getPageSource(self.url)
        d.addCallback(cbGotSource)
        return d

    def asDict(self):
        """Return a friendly dictionary of url/title/timestamp"""
        return dict(url = self.url, title = self.title,
                    timestamp = self.timestamp.asHumanly(), visits=self.visitCount)
        
class BookmarkVisit(Item):
    """A special visit that is used as visit.referrer if the visit was referred
    by being selected from a bookmark or shortcut. Should be a singleton and
    should only be used as a visit.referrer"""

    # XXX Not sure which attributes we need. Particularly referrer?
    url = attributes.bytes()
    title = attributes.bytes()
    
    referrer = attributes.reference(allowNone=True)

    schemaVersion = 1
    typeName = 'bookmark_visit'

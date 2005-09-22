from datetime import datetime

from zope.interface import implements

from axiom.item import Item
from axiom import attributes

from epsilon.extime import Time

from clickchronicle import iclickchronicle, indexinghelp

class Domain(Item):
    implements(iclickchronicle.IVisited)
    
    host = attributes.bytes()
    title = attributes.bytes()
    visitCount = attributes.integer(default=0)
    ignore = attributes.integer(default=0) # Boolean
    favIcon = attributes.reference()
    timestamp = attributes.timestamp()
    
    schemaVersion = 1
    typeName = 'domain'

    def asDict(self):
        return dict(url = self.host, title = self.title,
                    timestamp = (Time.fromDatetime(datetime.now())).asHumanly(), 
                    visits=self.visitCount)

    def asIcon(self):
        return self.favIcon
    
class Visit(Item):
    """I correspond to a webpage-visit logged by a clickchronicle user"""
    implements(iclickchronicle.IIndexable, iclickchronicle.IVisited)
    
    timestamp = attributes.timestamp()
    url = attributes.bytes()
    title = attributes.bytes()
    visitCount = attributes.integer(default=0)
    domain = attributes.reference(allowNone=False)
    referrer = attributes.reference()

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
        return dict(url = self.url, title = self.title,
                    timestamp = self.timestamp.asHumanly(), 
                    visits=self.visitCount)

    def asIcon(self):
        return self.domain.favIcon
        
class BookmarkVisit(Item):
    """A special visit that is used as visit.referrer if the visit was referred
    by being selected from a bookmark or shortcut. Should be a singleton and
    should only be used as a visit.referrer"""

    # XXX Not sure which attributes we need. Particularly referrer?
    url = attributes.bytes(default='bookmark')
    title = attributes.bytes(default='bookmark')
    
    referrer = attributes.reference(allowNone=True)

    schemaVersion = 1
    typeName = 'bookmark_visit'

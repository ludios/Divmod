from zope.interface import implements
from twisted.python.components import registerAdapter

from axiom.item import Item
from axiom import attributes

from clickchronicle import iclickchronicle, indexinghelp

class Domain(Item):
    url = attributes.bytes()
    title = attributes.bytes()
    visitCount = attributes.integer(default=0)
    ignore = attributes.boolean(default=False)
    favIcon = attributes.reference()
    timestamp = attributes.timestamp()

    schemaVersion = 1
    typeName = 'domain'

class DefaultDisplayableVisit:
    implements(iclickchronicle.IDisplayableVisit)

    def __init__(self, original):
        self.original = original

    def asDict(self):
        return dict(url=self.original.url, title=self.original.title, 
                    visitCount=self.original.visitCount, 
                    timestamp=self.original.timestamp)

class DisplayableDomain(DefaultDisplayableVisit):
    def asIcon(self):
        return self.original.favIcon

registerAdapter(DisplayableDomain,
                Domain,
                iclickchronicle.IDisplayableVisit)

class Visit(Item):
    """I correspond to a webpage-visit logged by a clickchronicle user"""
    implements(iclickchronicle.IIndexable)

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

class DisplayableVisit(DefaultDisplayableVisit):
    def asIcon(self):
        return self.original.domain.favIcon

registerAdapter(DisplayableVisit,
                Visit,
                iclickchronicle.IDisplayableVisit)

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

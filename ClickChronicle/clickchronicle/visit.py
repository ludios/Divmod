from zope.interface import implements
from twisted.python.components import registerAdapter
from axiom.item import Item
from axiom import attributes
from epsilon.extime import Time
from datetime import datetime

from clickchronicle import iclickchronicle, indexinghelp

class Domain(Item):
    url = attributes.bytes()
    title = attributes.text()
    visitCount = attributes.integer(default=0)
    ignore = attributes.boolean(default=False)
    favIcon = attributes.reference()
    timestamp = attributes.timestamp()

    schemaVersion = 1
    typeName = 'domain'

    def __repr__(self):
        return '<Domain %r>' % (self.url,)

class DefaultDisplayableVisit:
    implements(iclickchronicle.IDisplayableVisit)

    def __init__(self, original):
        self.original = original

    def asDict(self):
        return dict(url=self.original.url.decode('utf-8'),
                    title=self.original.title,
                    visitCount=self.original.visitCount,
                    timestamp=self.original.timestamp,
                    identifier=self.original.storeID)

class DisplayableDomain(DefaultDisplayableVisit):
    def asIcon(self):
        return self.original.favIcon

registerAdapter(DisplayableDomain,
                Domain,
                iclickchronicle.IDisplayableVisit)

class VisitMixin(object):
    def asDocument(self):
        """
        Return a Document in a Deferred.
        """
        def cbGotSource((pageSource, encoding)):
            doc = indexinghelp.makeDocument(self, pageSource, encoding)
            return doc
        d = iclickchronicle.ICache(self.store).getPageSource(self.url)
        d.addCallback(cbGotSource)
        return d

class Bookmark(Item, VisitMixin):
    """I correspond to a webpage-visit logged by a clickchronicle user"""
    implements(iclickchronicle.IIndexable)

    timestamp = attributes.timestamp()
    url = attributes.bytes()
    title = attributes.text()
    visitCount = attributes.integer(default=0)
    domain = attributes.reference(allowNone=False)
    referrer = attributes.reference()

    schemaVersion = 1
    typeName = 'bookmark'

class Visit(Item, VisitMixin):
    """I correspond to a webpage-visit logged by a clickchronicle user"""
    implements(iclickchronicle.IIndexable)

    timestamp = attributes.timestamp()
    url = attributes.bytes()
    title = attributes.text()
    visitCount = attributes.integer(default=0)
    domain = attributes.reference(allowNone=False)
    referrer = attributes.reference()

    schemaVersion = 1
    typeName = 'visit'

    def asBookmark(self):
        # TODO Detect duplicates
        dt=Time.fromDatetime(datetime.now())
        return Bookmark(store=self.store,
                        url=self.url,
                        title=self.title,
                        domain=self.domain,
                        timestamp=dt)

class DisplayableVisit(DefaultDisplayableVisit):
    def asIcon(self):
        return self.original.domain.favIcon

registerAdapter(DisplayableVisit,
                Visit,
                iclickchronicle.IDisplayableVisit)
registerAdapter(DisplayableVisit,
                Bookmark,
                iclickchronicle.IDisplayableVisit)

class BookmarkVisit(Item):
    """A special visit that is used as visit.referrer if the visit was referred
    by being selected from a bookmark or shortcut. Should be a singleton and
    should only be used as a visit.referrer"""

    # XXX Not sure which attributes we need. Particularly referrer?
    url = attributes.bytes(default='bookmark')
    title = attributes.text(default=u'bookmark')

    referrer = attributes.reference(allowNone=True)

    schemaVersion = 1
    typeName = 'bookmark_visit'

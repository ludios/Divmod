from zope.interface import implements
from axiom.item import Item
from axiom import attributes
from epsilon.extime import Time
from datetime import datetime

from clickchronicle import iclickchronicle, indexinghelp

class DisplayableVisitMixin(object):
    implements(iclickchronicle.IDisplayableVisit)

    def asDict(self):
        return dict(url=self.url.decode("utf-8"),
                    title=self.title,
                    visitCount=self.visitCount,
                    timestamp=self.timestamp,
                    identifier=self.storeID,
                    bookmarked=self.hasBookmark())

    def hasBookmark(self):
        for bookmark in self.store.query(Bookmark, Bookmark.url == self.url):
            return True

class Domain(Item, DisplayableVisitMixin):
    url = attributes.bytes(allowNone=False)
    title = attributes.text(allowNone=True) # We use None to denote that a title has not been set
    visitCount = attributes.integer(default=0)
    ignore = attributes.boolean(default=False)
    favIcon = attributes.reference(allowNone=True)
    timestamp = attributes.timestamp()

    schemaVersion = 1
    typeName = 'domain'

    def __repr__(self):
        return '<Domain %r>' % (self.url,)

    def asIcon(self):
        return self.favIcon

    def getLatest(self, count):
        return self.store.query(Domain, Domain.url == self.url,
                                sort=Domain.timestamp.desc, limit=count)
    def asBookmark(self):
        dt = Time.fromDatetime(datetime.now())
        referrer = self.store.findFirst(BookmarkVisit)
        bookmark = self.store.findOrCreate(Bookmark,
                                           url=self.url,
                                           title=self.title,
                                           domain=self,
                                           timestamp=dt,
                                           referrer=referrer)
        return bookmark

    def asDict(self):
        myDict = super(Domain, self).asDict()
        if self.title is None:
            myDict['title']=self.url
        return myDict

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

class Bookmark(Item, VisitMixin, DisplayableVisitMixin):
    """I correspond to a webpage-visit logged by a clickchronicle user"""
    implements(iclickchronicle.IIndexable)

    timestamp = attributes.timestamp()
    url = attributes.bytes(allowNone=False)
    title = attributes.text(allowNone=False)
    visitCount = attributes.integer(default=0)
    domain = attributes.reference(allowNone=False)
    referrer = attributes.reference(allowNone=False)

    schemaVersion = 1
    typeName = 'bookmark'

    def asIcon(self):
        return self.domain.favIcon

    def getLatest(self, count):
        return self.store.query(Bookmark, Bookmark.url == self.url,
                                sort=Bookmark.timestamp.desc, limit=count)

    def hasBookmark(self):
        return True

class Visit(Item, VisitMixin, DisplayableVisitMixin):
    """I correspond to a webpage-visit logged by a clickchronicle user"""
    implements(iclickchronicle.IIndexable)

    timestamp = attributes.timestamp()
    url = attributes.bytes(allowNone=False)
    title = attributes.text(allowNone=False)
    visitCount = attributes.integer(default=0)
    domain = attributes.reference(allowNone=False)
    referrer = attributes.reference(allowNone=False)

    schemaVersion = 1
    typeName = 'visit'

    def asBookmark(self):
        dt = Time.fromDatetime(datetime.now())
        bookmark = self.store.findOrCreate(Bookmark,
                                           url=self.url,
                                           title=self.title,
                                           domain=self.domain,
                                           referrer=self.referrer,
                                           timestamp=dt)
        return bookmark

    def asIcon(self):
        return self.domain.favIcon

    def getLatest(self, count):
        return self.store.query(Visit, Visit.url == self.url,
                                sort=Visit.timestamp.desc, limit=count)

class BookmarkVisit(Item):
    """A special visit that is used as visit.referrer if the visit was referred
    by being selected from a bookmark or shortcut. Should be a singleton and
    should only be used as a visit.referrer"""

    # XXX Not sure which attributes we need. Particularly referrer?
    url = attributes.bytes(default='Unavailable')
    title = attributes.text(default=u'Unavailable')

    referrer = attributes.reference(allowNone=True)

    schemaVersion = 1
    typeName = 'bookmark_visit'

from zope.interface import Interface, Attribute

class IDisplayableVisit(Interface):
    """
    I represent a displayable view of a visitable Item
    """

    def asDict(self):
        """
        Return a dictionary summarizing my more useful attributes
        """

    def asIcon(self):
        """
        Return FavIcon item associated with this visit
        """

    def getLatest(self, count):
        """
        Return "count" latest visits to similar resources
        """

    def hasBookmark(self):
        """
        Return boolean indicating whether this visit has an associated bookmark
        """

class IIndexer(Interface):
    """
    Interface for providing full-text indexing services.
    """

    def index(self, item):
        """
        Index and item for later search.
        """

    def search(self, aString):
        """
        Search the index for aString and return results.
        """

    def count(self, aString):
        """
        Return a 2-tuple of (estimated-matches, total-docs-indexed)
        """

class ICache(Interface):
    """
    Interface for fetching and caching data from external sources.
    """


class IIndexable(Interface):
    """
    Something that can be indexed by an IIndexer.
    """

    def asDocument(self):
        """Return a Deferred that reutrns a xapwrap.Document
        containing the text and fields for indexing by IIndexer.
        """


class IClickRecorder(Interface):
    """
    ClickRecorder interface.
    """

class IClickList(Interface):
    """
    An upgrader will need to be written here.
    """

    clicks = Attribute('allowed for sharing')
    store = Attribute('allowed for sharing')

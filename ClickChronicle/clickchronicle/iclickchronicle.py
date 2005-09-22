from zope.interface import Interface, Attribute

class IVisited(Interface):
    """
    I represent a web-accessible resource visited by a clickchronicle user
    """

    title = Attribute("string - title/display name of resource")
    visitCount = Attribute("integer - number of times user visited resource")
    timestamp = Attribute("extime.Time - timestamp of last recorded visit")

    def asDict(self):
        """
        Return a dictionary summarizing my attributes
        """

    def asIcon(self):
        """
        Return FavIcon Item associated with visited resource
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


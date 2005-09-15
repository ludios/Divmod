import os

from zope.interface import implements

from axiom.item import Item
from axiom import attributes

from clickchronicle import indexinghelp

            
class Domain(Item):
    name = attributes.bytes()
    title = attributes.bytes()
    visitCount = attributes.integer(default=0)

    schemaVersion = 1
    typeName = 'domain'

class Visit(Item):
    """I correspond to a webpage-visit logged by a clickchronicle user"""
    implements(indexinghelp.IIndexable)
    timestamp = attributes.timestamp()
    url = attributes.bytes()
    title = attributes.bytes()
    visitCount = attributes.integer(default=1)
    domain = attributes.reference(allowNone = False)

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
        
    def cachePage(self, pageSource):
        """
        Cache the source for this Visit.
        """
        newFile = self.store.newFile(self.cachedFileName())
        newFile.write(pageSource)
        newFile.close()

    def cachedFileName(self):
        """
        Return the path to the cached source for this visit.
        The path consists of the iso date for the visit as directory and the
        storeID as the filename.
        e.g. cchronicle.axiom/files/account/test.com/user/files/cache/2005-09-10/55.html
        """
        # XXX - I doubt that this is how these path objects are supposed to
        # be manipulated. Check for sanity/style.
        dirName = self.timestamp.asDatetime().date().isoformat()
        cacheDir = self.store.newDirectory('cache/%s' % dirName)
        fileName = str(cacheDir.path)+ '/' + str(self.storeID) + '.html'
        return fileName

    def forget(self):
        fName = self.cachedFileName()
        os.remove(fName)

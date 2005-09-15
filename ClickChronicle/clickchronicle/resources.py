from nevow import rend, livepage, inevow, tags
from clickchronicle.indexinghelp import SyncIndexer
from clickchronicle.util import PagedTableMixin
from clickchronicle.searchparser import parseSearchString
from clickchronicle.items.common import Visit

class CCFragment(rend.Fragment):
    searchFactory = None
    def render_search(self, ctx, data):
        if self.searchFactory is None:
            self.searchFactory = self.page.webapp.getDocFactory('search')
        return ctx.tag.clear()[rend.Fragment(docFactory=self.searchFactory)]
    
class PreferencesFragment(CCFragment):
    """I will get an adapter for Preferences instances, who
       implements INavigableFragment"""
       
    fragmentName = 'preferences-fragment'
    title = ''
    live = True

    def head(self):
        return None

    def data_preferences(self, ctx, data):
        """return a dict of self.original's (Preferences instance) columns"""
        return dict(displayName = self.original.displayName,
                     homepage = self.original.homepage)

class CCPagedTableMixin(PagedTableMixin):
    def makeScriptTag(self, src):
        return tags.script(type='application/x-javascript', 
                           src=src)
    def head(self):
        return self.makeScriptTag('/static/js/paged-table.js')

class ClickListFragment(CCFragment, CCPagedTableMixin):
    '''i adapt ClickList to INavigableFragment'''
    
    fragmentName = 'click-list-fragment'
    title = ''
    matchingClicks = 0
    discriminator = ''
    maxTitleLength = 85
    live = True
    
    def __init__(self, original, docFactory=None):
        rend.Fragment.__init__(self, original, docFactory)
        (self.indexer,) = list(original.store.query(SyncIndexer))
        
    def trimTitle(self, visitDict):
        title = visitDict['title']
        if self.maxTitleLength < len(title):
            visitDict['title'] = '%s...' % title[:self.maxTitleLength - 3]
        return visitDict
            
    def matchingRowDicts(self, ctx, pageNumber, itemsPerPage):
        offset = (pageNumber - 1) * itemsPerPage
        specs = self.indexer.search(self.discriminator,
                                    startingIndex = offset,
                                    batchSize = itemsPerPage)
        store = self.original.store
        for spec in specs:
            (visit,) = list(store.query(Visit, Visit.storeID == spec['uid']))
            yield self.trimTitle(visit.asDict())

    def allRowDicts(self, ctx, pageNumber, itemsPerPage):
        store = self.original.store 
        offset = (pageNumber - 1) * itemsPerPage
        
        for v in store.query(Visit, sort = Visit.timestamp.descending,
                             limit = itemsPerPage, offset = offset):
            
            yield self.trimTitle(v.asDict())

    def generateRowDicts(self, ctx, pageNumber, itemsPerPage):
        if self.discriminator:
            return self.matchingRowDicts(ctx, pageNumber, itemsPerPage)
        else:
            return self.allRowDicts(ctx, pageNumber, itemsPerPage)
        
    def countTotalItems(self, ctx):
        return self.original.clicks
        
    def handle_filter(self, ctx, discriminator):
        self.discriminator = ' '.join(parseSearchString(discriminator))
        (estimated, total) = self.indexer.count(self.discriminator)
        yield self.updateTable(ctx, self.startPage, self.defaultItemsPerPage)
        yield (livepage.js.setTotalItems(estimated), livepage.eol)

class URLGrabber(rend.Page):
    """I handle ClickRecorder's HTTP action.  i am not an Item
       because i have a lot of attributes inherited from rend.Page"""
    def __init__(self, recorder):
        self.recorder = recorder
        
    def renderHTTP(self, ctx):
        """get url and title GET variables, supplying sane defaults"""
        urlpath = inevow.IRequest(ctx).URLPath()
        qargs = dict(urlpath.queryList())
        self.recorder.recordClick(qargs)
        return ''

from __future__ import division
from nevow import livepage
from math import ceil
from twisted.internet.defer import maybeDeferred
from twisted.python.util import mergeFunctionMetadata

def maybeDeferredWrapper(f):
    """nicer than maybeDeferred.__get__"""
    def wrapped(*a, **k):
        return maybeDeferred(f, *a, **k)
    return mergeFunctionMetadata(f, wrapped)

class PagedTableMixin:
    itemsPerPage = 10
    startPage = 1

    patterns = None

    def data_totalItems(self, ctx, data):
        return self.countTotalItems(ctx)

    def render_navBar(self, ctx, data):
        pageNumData = self.calculatePages(ctx)
        content = self.patterns["navBar"].fillSlots('pagingWidget',
                        self.patterns["pagingWidget"](data=pageNumData))

        return ctx.tag[content]

    def handle_updateTable(self, ctx, pageNumber, *args):
        pageNumber = int(pageNumber)
        rowDicts = list(self.generateRowDicts(ctx, pageNumber, *args))
        offset = (pageNumber - 1) * self.itemsPerPage

        yield (livepage.set('tableContainer', self.constructTable(ctx, rowDicts)), livepage.eol)
        yield (livepage.set('startItem', offset + 1), livepage.eol)
        yield (livepage.set('endItem', offset + len(rowDicts)), livepage.eol)
        yield (livepage.js.setTotalItems(self.countTotalItems(ctx)), livepage.eol)

    def calculatePages(self, ctx):
        totalItems = self.countTotalItems(ctx)
        return xrange(1, int(ceil(totalItems / self.itemsPerPage))+1)

    def goingLive(self, ctx, client, *args):
        client.send(self.handle_updateTable(ctx, self.startPage, *args))

    # override these methods
    def generateRowDicts(self, ctx, pageNumber):
        """I return a sequence of dictionaries that will be used as data for
           the constructTable method

           pageNumber: number of page currently being viewed, starting from 1, not 0"""

        raise NotImplementedError

    def countTotalItems(self, ctx):
        raise NotImplementedError

    def constructTable(self, ctx, rows):
        raise NotImplementedError

class SortablePagedTableMixin(PagedTableMixin):
    sortColumn = None
    sortDirection = None

    def goingLive(self, ctx, client):
        PagedTableMixin.goingLive(self, ctx, client, self.sortColumn,
                                  self.sortDirection)
        client.call('setSortState', self.sortColumn,
                    self.sortDirection)

    def handle_updateTable(self, ctx, pageNumber,
                           sortColumn=None, sortDirection=None):

        if sortColumn is None:
            sortColumn = self.sortColumn
        elif self.sortColumn != sortColumn:
            pageNumber = self.startPage
            self.sortColumn = sortColumn

        if sortDirection is None:
            sortDirection = self.sortDirection
        else:
            self.sortDirection = sortDirection

        yield PagedTableMixin.handle_updateTable(self, ctx, pageNumber,
                                                 sortColumn, sortDirection)

        yield livepage.js.setSortState(self.sortColumn, self.sortDirection), livepage.eol

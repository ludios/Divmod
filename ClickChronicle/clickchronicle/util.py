from __future__ import division
from nevow import livepage
from math import ceil

class PagedTableMixin:
    itemsPerPage = (10, 20, 50, 100)
    defaultItemsPerPage = 10
    startPage = 1

    tablePattern = None
    pageNumbersPattern = None
    itemsPerPagePattern = None
    navBarPattern = None
    
    def data_totalItems(self, ctx, data):
        return self.countTotalItems(ctx)

    def handle_updateTable(self, ctx, pageNumber, itemsPerPage):
        yield (self.updateTable(ctx, pageNumber, itemsPerPage), livepage.eol)
        yield (self.changeItemsPerPage(ctx, pageNumber, itemsPerPage), livepage.eol)

    def render_navBar(self, ctx, data):
        pageNumData = self.calculatePages(ctx, self.defaultItemsPerPage)
        content = self.navBarPattern.fillSlots(
                      'itemsPerPage', self.itemsPerPagePattern(data=self.itemsPerPage)
                  ).fillSlots(
                      'pagingWidget', self.pageNumbersPattern(data=pageNumData))
                  
        return ctx.tag[content]
    
    def updateTable(self, ctx, pageNumber, itemsPerPage):
        (pageNumber, itemsPerPage) = (int(pageNumber), int(itemsPerPage))
        
        rowDicts = list(self.generateRowDicts(ctx, pageNumber, itemsPerPage))
        
        table = self.tablePattern(data=rowDicts)
        offset = (pageNumber - 1) * itemsPerPage
        
        yield (livepage.set('tableContainer', table), livepage.eol)
        yield (livepage.set('startItem', offset + 1), livepage.eol)
        yield (livepage.set('endItem', offset + len(rowDicts)), livepage.eol)

    def handle_changeItemsPerPage(self, ctx, pageNumber, perPage):
        yield (self.updateTable(ctx, 1, perPage), livepage.eol)
        yield (self.changeItemsPerPage(ctx, 1, perPage), livepage.eol)

    def calculatePages(self, ctx, perPage):
        perPage = int(perPage)
        totalItems = self.countTotalItems(ctx)
        return xrange(1, int(ceil(totalItems / perPage))+1)
            
    def changeItemsPerPage(self, ctx, pageNumber, perPage):
        pagingWidget = self.pageNumbersPattern(data=self.calculatePages(ctx, perPage))
        yield (livepage.set('pagingWidgetContainer', pagingWidget), livepage.eol)
        yield (livepage.js.setCurrentPage(pageNumber), livepage.eol)
    
    def goingLive(self, ctx, client):
        client.call('setItemsPerPage', self.defaultItemsPerPage)
        client.send(self.updateTable(ctx, self.startPage, self.defaultItemsPerPage))
        client.send(self.changeItemsPerPage(ctx, self.startPage, self.defaultItemsPerPage))

    # override these methods
    def generateRowDicts(self, ctx, pageNumber, itemsPerPage):
        """I return a sequence of dictionaries that will be used as data for
           the corresponding template's 'table' pattern.

           pageNumber: number of page currently being viewed, starting from 1, not 0"""
                       
        raise NotImplementedError

    def countTotalItems(self, ctx):
        raise NotImplementedError

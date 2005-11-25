from pytz import timezone
from nevow import tags

from xmantissa import ixmantissa, tdb, tdbview

from clickchronicle.visit import Bookmark
from clickchronicle import iclickchronicle, indexinghelp


def makeClickTDM(store, typeClass):
    prefs = ixmantissa.IPreferenceAggregator(store)

    tdm = tdb.TabularDataModel(store,
                typeClass, [typeClass.timestamp,
                            typeClass.title,
                            typeClass.visitCount],
                itemsPerPage=prefs.getPreferenceValue('itemsPerPage'),
                defaultSortAscending=False)


    views = [TimezoneColumnView('timestamp'),
             FaviconVisitLinkColumnView('title', width='100%'),
             tdbview.ColumnViewBase('visitCount', typeHint='numeric',
                                     displayName='Visits')]

    return (tdm, views)

class FaviconVisitLinkColumnView(tdbview.ColumnViewBase):
    maxLength = 70

    def __init__(self, attributeID, displayName=None,
                 width=None, typeHint='text'):

        tdbview.ColumnViewBase.__init__(self, attributeID, displayName,
                                        width, typeHint)

    def stanFromValue(self, idx, item, value):
        if value is None:
            value = item.url

        if self.maxLength < len(value):
            value = value[:self.maxLength-3] + '...'

        return (tags.img(src=item.asIcon().iconURL, width=16, height=16,
                         **{'class':'clickchronicle-favicon'}),
                tags.a(href=item.url)[value])

class TimezoneColumnView(tdbview.DateColumnView):
    tzinfo = None

    def stanFromValue(self, idx, item, value):
        if self.tzinfo is None:
            prefs = ixmantissa.IPreferenceAggregator(item.store)
            tzname = prefs.getPreferenceValue('timezone')
            self.tzinfo = timezone(tzname)

        return value.asHumanly(self.tzinfo)

class BookmarkAction(tdbview.Action):
    def __init__(self):
        tdbview.Action.__init__(self, 'bookmark',
                                '/static/images/bookmark.png',
                                'Bookmark this visit',
                                disabledIconURL='/static/images/bookmark_disabled.png')

    def performOn(self, visit):
        visit.asBookmark()
        return 'Bookmarked %s' % (visit.url,)

    def actionable(self, visit):
        return visit.store.count(Bookmark, Bookmark.url == visit.url) == 0

bookmarkAction = BookmarkAction()

class IgnoreAction(tdbview.Action):
    def __init__(self):
        tdbview.Action.__init__(self, 'ignore',
                                '/static/images/ignore_link.png',
                                'Ignore this visit')

    def performOn(self, visit):
        recorder = iclickchronicle.IClickRecorder(visit.store)
        recorder.ignoreVisit(visit)
        return 'Ignored %s' % (visit.url,)

    def actionable(self, visit):
        return True

ignoreAction = IgnoreAction()

class DeleteAction(tdbview.Action):
    def __init__(self):
        tdbview.Action.__init__(self, 'delete',
                                '/static/images/delete.png',
                                'Delete this visit')

    def performOn(self, visit):
        iclickchronicle.IClickRecorder(visit.store).forgetVisit(visit)
        return 'Deleted %s' % (visit.url,)

    def actionable(self, visit):
        return True

deleteAction = DeleteAction()
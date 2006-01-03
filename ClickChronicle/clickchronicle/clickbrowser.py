from pytz import timezone
from nevow import tags

from xmantissa import ixmantissa, tdb, tdbview

from clickchronicle.visit import Bookmark
from clickchronicle import iclickchronicle, indexinghelp


def trimFeedbackURL(url, maxlength=50):
    if maxlength < len(url):
        url = url[:maxlength-3] + '...'
    return url

def makeClickTDM(store, typeClass, baseComparison=None):
    prefs = ixmantissa.IPreferenceAggregator(store)

    tdm = tdb.TabularDataModel(store,
                typeClass, [typeClass.timestamp,
                            typeClass.title,
                            typeClass.visitCount],
                itemsPerPage=prefs.getPreferenceValue('itemsPerPage'),
                baseComparison=baseComparison,
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
                                '/ClickChronicle/static/images/bookmark.png',
                                'Bookmark this visit',
                                disabledIconURL='/ClickChronicle/static/images/bookmark_disabled.png')

    def performOn(self, visit):
        visit.asBookmark()
        return u'Bookmarked %s' % (trimFeedbackURL(visit.url),)

    def actionable(self, visit):
        return visit.store.count(Bookmark, Bookmark.url == visit.url) == 0

bookmarkAction = BookmarkAction()

class IgnoreVisitAction(tdbview.Action):
    def __init__(self):
        tdbview.Action.__init__(self, 'ignore',
                                '/ClickChronicle/static/images/ignore.png',
                                'Ignore this visit')

    def performOn(self, visit):
        recorder = iclickchronicle.IClickRecorder(visit.store)
        recorder.ignoreVisit(visit)
        return u'Ignored %s' % (trimFeedbackURL(visit.url),)

    def actionable(self, visit):
        return True

ignoreVisitAction = IgnoreVisitAction()

class DeleteAction(tdbview.Action):
    def __init__(self):
        tdbview.Action.__init__(self, 'delete',
                                '/ClickChronicle/static/images/delete.png',
                                'Delete this visit')

    def performOn(self, visit):
        cr = iclickchronicle.IClickRecorder(visit.store)
        if hasattr(visit, 'domain'):
            cr.forgetVisit(visit)
        else:
            cr.deleteDomain(visit)
        return u'Deleted %s' % (trimFeedbackURL(visit.url),)

    def actionable(self, visit):
        return True

deleteAction = DeleteAction()

class BlockDomainToggleAction(tdbview.ToggleAction):
    def __init__(self):
        tdbview.ToggleAction.__init__(self, 'block',
                                      '/ClickChronicle/static/images/ignore.png',
                                      'Block/Unblock this domain',
                                      disabledIconURL='/ClickChronicle/static/images/ignore-disabled.png')

    def isOn(self, idx, domain):
        return not domain.ignore

    def performOn(self, domain):
        if domain.ignore:
            domain.ignore = False
            word = 'Unblocked'
        else:
            iclickchronicle.IClickRecorder(domain.store).ignoreVisit(domain)
            word = 'Blocked'

        return word  + u' ' + trimFeedbackURL(domain.url)

blockDomainToggleAction = BlockDomainToggleAction()

class PrivateToggleAction(tdbview.ToggleAction):
    def __init__(self):
        tdbview.ToggleAction.__init__(self, 'private',
                                      '/ClickChronicle/static/images/private.png',
                                      'Mark this domain private/public',
                                      disabledIconURL='/ClickChronicle/static/images/private-disabled.png')

    def isOn(self, idx, domain):
        return not domain.private

    def performOn(self, domain):
        domain.private = not domain.private
        word = ('public', 'private')[domain.private]
        return u'Marked %s %s' % (trimFeedbackURL(domain.url), word)

privateToggleAction = PrivateToggleAction()

class PrivateVisitToggleAction(PrivateToggleAction):
    def performOn(self, visit):
        return PrivateToggleAction.performOn(self, visit.domain)

    def isOn(self, idx, visit):
        return PrivateToggleAction.isOn(self, idx, visit.domain)

privateVisitToggleAction = PrivateVisitToggleAction()

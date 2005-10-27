# -*- clickchronicle.test.test_upgraders -*-

"""
Axiom upgrade functions for ClickChronicle
"""

from epsilon import extime

from axiom.upgrade import registerUpgrader

def publicPage1To2(oldpage):
    newpage = oldpage.upgradeVersion("clickchronicle_public_page", 1, 2)
    newpage.lastIntervalEnd = extime.Time()
    return newpage

registerUpgrader(publicPage1To2, "clickchronicle_public_page", 1, 2)

def publicPage2To3(oldpage):
    newpage = oldpage.upgradeVersion("clickchronicle_public_page", 2, 3)
    newpage.totalClicks = 0
    return newpage

registerUpgrader(publicPage2To3, "clickchronicle_public_page", 2, 3)

from axiom.store import Store
from xapwrap.document import Document, Value, Keyword
from xapwrap.index import SmartIndex, DocNotFoundError
from clickchronicle.visit import Visit

def upgradeXap():
    store=Store('amir')
    db = SmartIndex('amir/files/xap.index', True)
    d=Document(keywords=[Keyword('_STOREID', '0'),Keyword('_TYPE','0')],values=Value('_STOREID','0'))
    fixerID = db.index(d)
    db.db.delete_document(fixerID)
    storeidIndex = db.indexValueMap['_STOREID']
    typeIndex = db.indexValueMap['type']
    for visit in store.query(Visit):
        sid = visit.storeID
        try:
            print 'fetching', sid
            doc=db.db.get_document(sid)
            # use for deletion
            doc.add_term('_STOREID'+str(sid))
            doc.add_term('_TYPE'+'click')
            # used for retrieval
            doc.add_value(storeidIndex, str(sid))
            doc.remove_value(typeIndex)
            doc.add_value(typeIndex, 'click')
            print db.db.add_document(doc)
            db.db.delete_document(sid)
        except DocNotFoundError:
            print 'not found', sid

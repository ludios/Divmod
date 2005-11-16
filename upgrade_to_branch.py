from clickchronicle.indexinghelp import DefaultFavicon
from clickchronicle.visit import Domain
from axiom.store import Store
from axiom.substore import SubStore

def txn():
    for substore in store.query(SubStore):
        substore = substore.open()
        df = substore.findOrCreate(DefaultFavicon)
        for d in substore.query(Domain, Domain.favIcon == None):
            d.favIcon = df
        for d in substore.query(Domain, Domain.title == None):
            d.title = unicode(d.url)

store = Store('cchronicle.axiom')
store.transact(txn)

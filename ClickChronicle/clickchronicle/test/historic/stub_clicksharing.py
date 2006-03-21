
from clickchronicle.clickapp import CCPreferenceCollection, ClickList

def createDatabase(s):
    ClickList(store=s, clicks=0).installOn(s)
    ccpc = CCPreferenceCollection(store=s)
    ccpc.installOn(s)
    ccpc.publicPage = True

from axiom.test.historic.stubloader import saveStub

if __name__ == '__main__':
    saveStub(createDatabase, 5532)

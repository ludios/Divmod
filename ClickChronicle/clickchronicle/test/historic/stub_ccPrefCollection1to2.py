
from clickchronicle import clickapp

def createDatabase(s):
    clickapp.CCPreferenceCollection(
                store=s,
                shareClicks=True).installOn(s)

from axiom.test.historic.stubloader import saveStub

if __name__ == '__main__':
    saveStub(createDatabase)

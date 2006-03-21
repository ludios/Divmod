
from clickchronicle import publicpage

def createDatabase(s):
    publicpage.ClickStats(
        store=s,
        score=22,
        history=publicpage._saveHistory([1, 2, 3]),
        url='http://example.com/',
        title=u'Example Dot Com',
        statKeeper=None)

from axiom.test.historic.stubloader import saveStub

if __name__ == '__main__':
    saveStub(createDatabase)


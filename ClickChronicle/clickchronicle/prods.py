# -*- test-case-name: clickchronicle.test.test_products -*-

"""
Products related to ClickChronicle to be offered for sale.
"""

from zope.interface import implements

from twisted.cred import portal

from axiom import item, attributes

from xmantissa import ixmantissa

from clickchronicle import iclickchronicle

class ClickIncreaser(item.Item):
    implements(ixmantissa.IBenefactor)

    typeName = 'clickchronicle_morequota_benefactor'
    schemaVersion = 1

    # How many more stored clicks buying this gets you.
    clickChange = attributes.integer()

    def __repr__(self):
        return 'ClickIncreaser: %d clicks' % (self.clickChange,)

    def installOn(self, other):
        other.powerUp(self, ixmantissa.IBenefactor)

    def uninstallFrom(self, other):
        other.powerDown(self, ixmantissa.IBenefactor)

    def endow(self, ticket, avatar):
        recorder = iclickchronicle.IClickRecorder(avatar)
        recorder.maxCount += self.clickChange

    def deprive(self, ticket, avatar):
        recorder = iclickchronicle.IClickRecorder(avatar)
        recorder.maxCount -= self.clickChange

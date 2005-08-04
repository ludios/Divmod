
import os, sys

from zope.interface import classProvides

from twisted.python import usage
from twisted import plugin

from axiom import store, item, iaxiom

from radical import radapp

class RadicalConfiguration(usage.Options):
    classProvides(plugin.IPlugin, iaxiom.IAxiomaticCommand)

    name = 'radical'
    description = 'omfg play the game now'

    def postOptions(self):
        s = self.parent.getStore()
        radapp.RadicalApplication(store=s).install()

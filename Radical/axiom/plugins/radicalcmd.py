
import os, sys

from zope.interface import classProvides

from twisted.python import usage
from twisted import plugin

from axiom import store, item, iaxiom

from xmantissa import signup

from radical import radapp

class RadicalConfiguration(usage.Options):
    classProvides(plugin.IPlugin, iaxiom.IAxiomaticCommand)

    name = 'radical'
    description = 'omfg play the game now'

    optFlags = [
        ('world', 'w', 'Install a world on the given database'),
        ]

    def postOptions(self):
        s = self.parent.getStore()
        def postOptions():
            if self['world']:
                for world in s.store.query(radapp.RadicalWorld):
                    break
                else:
                    radapp.RadicalWorld(store=s.store).install()
            else:
                radapp.RadicalApplication(store=s).install()
        s.transact(postOptions)

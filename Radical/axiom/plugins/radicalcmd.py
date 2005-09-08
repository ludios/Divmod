
import os, sys

from zope.interface import classProvides

from twisted.python import usage
from twisted import plugin

from axiom import store, item, iaxiom, scheduler

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
                for sch in s.store.query(scheduler.Scheduler):
                    break
                else:
                    sch = scheduler.Scheduler(store=s)
                    sch.installOn(s)
                    sch.checkpoint()
                    s.checkpoint()

                for world in s.store.query(radapp.RadicalWorld):
                    break
                else:
                    radapp.RadicalWorld(store=s).installOn(s)
            else:
                radapp.RadicalApplication(store=s).installOn(s)
        s.transact(postOptions)


from axiom import iaxiom, scheduler

from xmantissa import offering

import radical
from radical import radapp

offer = offering.Offering(
    name = u"Radical",
    description = u"""
    Radical is an awesome game for you to play.
    """,
    siteRequirements = (
        (iaxiom.IScheduler, scheduler.Scheduler),
        (None, radapp.RadicalWorld),
        ),
    appPowerups = (
        radapp.RadicalApplication,
        ),
    benefactorFactories = (
    ))


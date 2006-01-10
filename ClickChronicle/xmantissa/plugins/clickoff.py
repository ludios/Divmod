# -*- test-case-name: xmantissa.test.test_signup -*-

from axiom import iaxiom, scheduler, userbase

from xmantissa import liveform, website, offering, provisioning

import clickchronicle

from clickchronicle import clickapp, publicpage, prods

ccBenefactorArgs = [
    liveform.Parameter('maxClicks',
         liveform.TEXT_INPUT,
         int,
         u'The number of clicks users will be allowed to store at once.',
         u'1000')
    ]

chronicler = provisioning.BenefactorFactory(
    name = u'clickchronicle',
    description = u'An application with which to chronicle the clicks of you.',
    benefactorClass = clickapp.ClickChronicleBenefactor,
    parameters = ccBenefactorArgs,
    )

ccIncreaserArgs = [
    liveform.Parameter('clickChange',
         liveform.TEXT_INPUT,
         int,
         u'The number of additional clicks users will be allowed to store at once.',
         u'1000')
    ]

clicks = provisioning.BenefactorFactory(
    name = u'clickchronicle-clicks',
    description = u'Add some clicks to the click limit',
    benefactorClass = prods.ClickIncreaser,
    dependencies = [chronicler],
    parameters = ccIncreaserArgs,
    )

plugin = offering.Offering(
    name = u"ClickChronicle",

    description = u"""
    To-morrow, and to-morrow, and to-morrow,
    Creeps in this petty pace from day to day,
    To the last syllable of recorded time;
    And all our yesterdays have lighted fools
    The way to dusty death. Out, out, brief candle!
    Life's but a walking shadow; a poor player,
    That struts and frets his hour upon the stage,
    And then is heard no more: it is a tale
    Told by an idiot, full of sound and fury,
    Signifying nothing.
    """,

    siteRequirements = (
        (iaxiom.IScheduler, scheduler.Scheduler),
        (userbase.IRealm, userbase.LoginSystem),
        (None, website.WebSite)),

    appPowerups = (
        clickapp.StaticShellContent,
        publicpage.ClickChroniclePublicPage),

    benefactorFactories = (chronicler, clicks))


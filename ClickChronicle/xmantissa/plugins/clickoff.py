# -*- test-case-name: xmantissa.test.test_signup -*-

from axiom import iaxiom, scheduler, userbase

from xmantissa import website, offering

from clickchronicle import clickapp, publicpage, cctheme

plugin = offering.Offering(
    name = u"ClickChronicle",

    description = u"""
    An application for recording and reporting users' web viewing history.
    """,

    siteRequirements = (
        (iaxiom.IScheduler, scheduler.Scheduler),
        (userbase.IRealm, userbase.LoginSystem),
        (None, website.WebSite)),

    appPowerups = (
        clickapp.StaticShellContent,
        publicpage.ClickChroniclePublicPage),
    installablePowerups = (),
    loginInterfaces = (),
    themes=[cctheme.ClickChronicleTheme('cc-base', 0)])


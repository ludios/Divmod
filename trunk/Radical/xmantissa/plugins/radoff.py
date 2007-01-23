
from nevow import inevow

from xmantissa import website, offering

from radical import model, web, radtheme

offer = offering.Offering(
    name = u"Radical",
    description = u"""
    Radical is an awesome game for you to play.
    """,
    siteRequirements = [
        (inevow.IResource, website.WebSite)],
    appPowerups = [model.Game],
    installablePowerups = [],
    loginInterfaces=(),
    themes=[radtheme.XHTMLDirectoryTheme('base')])

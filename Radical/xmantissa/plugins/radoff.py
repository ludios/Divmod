
from nevow import inevow

from xmantissa import website, offering, provisioning

from radical import model, web, radtheme

offer = offering.Offering(
    name = u"Radical",
    description = u"""
    Radical is an awesome game for you to play.
    """,
    siteRequirements = [
        (inevow.IResource, website.WebSite)],
    appPowerups = [model.Game],
    benefactorFactories = [
        provisioning.BenefactorFactory(
            u'Radical Game',
            u'Grants a user access to a Radical game.',
            web.RadicalBenefactor)],
    themes=[radtheme.XHTMLDirectoryTheme('base')])

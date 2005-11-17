# -*- clickchronicle.test.test_upgraders -*-

"""
Axiom upgrade functions for ClickChronicle
"""

from epsilon import extime

from axiom.upgrade import registerUpgrader

# remember to set installedOn when you upgrade

def favicon1To2(oldicon):
    return oldicon.upgradeVersion("favicon", 1, 2,
                                  iconURL='/' + oldicon.prefixURL,
                                  prefixURL=oldicon.prefixURL,
                                  data=oldicon.data,
                                  contentType=oldicon.contentType)

registerUpgrader(favicon1To2, "favicon", 1, 2)

def publicPage1To2(oldpage):
    newpage = oldpage.upgradeVersion("clickchronicle_public_page", 1, 2)
    newpage.lastIntervalEnd = extime.Time()
    return newpage

registerUpgrader(publicPage1To2, "clickchronicle_public_page", 1, 2)

def publicPage2To3(oldpage):
    newpage = oldpage.upgradeVersion("clickchronicle_public_page", 2, 3)
    newpage.totalClicks = 0
    return newpage

registerUpgrader(publicPage2To3, "clickchronicle_public_page", 2, 3)

def publicPage3To4(oldpage):
    newpage = oldpage.upgradeVersion("clickchronicle_public_page", 3, 4)
    newpage.totalClicks = oldpage.totalClicks
    newpage.installedOn = oldpage.installedOn
    newpage.interval = 60 * 60
    return newpage

registerUpgrader(publicPage3To4, "clickchronicle_public_page", 3, 4)


def clickStat1to2(oldstat):
    from clickchronicle.publicpage import _saveHistory
    newstat = oldstat.upgradeVersion("click_stats", 1, 2, url=oldstat.url)
    newstat.score = 0
    newstat.history = _saveHistory([])
    newstat.title = oldstat.title
    newstat.totalClicks = oldstat.totalClicks
    newstat.intervalClicks = 0
    newstat.depth = oldstat.depth
    newstat.lastClickInterval = 0 # this iVar was added
    newstat.statKeeper = oldstat.statKeeper
    return oldstat

registerUpgrader(clickStat1to2, "click_stats", 1, 2)

def clickStat2to3(oldstat):
    from clickchronicle.publicpage import _loadHistory

    newstat = oldstat.upgradeVersion("click_stats", 2, 3,
                                     url=oldstat.url,
                                     score=0.,
                                     history=oldstat.history,
                                     title=oldstat.title,
                                     totalClicks=oldstat.totalClicks,
                                     intervalClicks=oldstat.intervalClicks,
                                     depth=oldstat.depth,
                                     lastClickInterval=oldstat.lastClickInterval,
                                     statKeeper=oldstat.statKeeper)

    # XXX ugh, remember to remove/update this when you write the next
    # upgrader...
    newstat.updateScore()
    return newstat

registerUpgrader(clickStat2to3, "click_stats", 2, 3)

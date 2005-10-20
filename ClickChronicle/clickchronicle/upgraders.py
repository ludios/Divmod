# -*- clickchronicle.test.test_upgraders -*-

"""
Axiom upgrade functions for ClickChronicle
"""

from epsilon import extime

from axiom.upgrade import registerUpgrader

def publicPage1To2(oldpage):
    newpage = oldpage.upgradeVersion("clickchronicle_public_page", 1, 2)
    newpage.lastIntervalEnd = extime.Time()
    return newpage

registerUpgrader(publicPage1To2, "clickchronicle_public_page", 1, 2)

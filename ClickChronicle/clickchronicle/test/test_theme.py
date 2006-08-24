from twisted.trial.unittest import TestCase

from xmantissa.test.test_theme import testHead
from clickchronicle.cctheme import ClickChronicleTheme

class ClickChronicleThemeTestCase(TestCase):
    def test_head(self):
        testHead(ClickChronicleTheme(''))

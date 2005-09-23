from twisted.trial.unittest import TestCase
from clickchronicle.tagstrip import cook

htmls = {'<SCRIPT>cruft {1+2=3<HTML>}</script>want want want<b></i><hello/><hoodwink>want' : 4,
         '<style type="text/css">.ploop { border: none; }></style>want<i>want</b>' : 2,
         'want want want want<ul><li>want<ol><li>want</li></ol></li>want</ul>want' : 8,
         'want' : 1,
         '<really bad html>want</really bad html>want' : 2,
         '<style/>take me out to the ballgame &#123</style>want <xyz/> want' : 2,
         '<style>1+2=3</style><script>function f(x) { 3+2-6**2/231 }</script><x onload="alert(f())">want' : 1}

class StripTagsTestCase(TestCase):
    def testStripping(self):
        for (html, expectedWants) in htmls.iteritems():
            (wants, meta) = cook(html)
            wants = wants.split()
            self.assertEqual(len(set(wants)), 1, 'expected uniform stripTags result')
            self.assertEqual(wants[0], 'want', 'expected only "want" from stripTags')
            self.assertEqual(len(wants), expectedWants,
                             'wanted %d wants from "%s"' % (expectedWants, html))

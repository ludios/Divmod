from clickchronicle import urltagger
from twisted.trial import unittest

class URLTaggerTestCase(unittest.TestCase):
    def assertOnlyTag(self, items, tag):
        for item in items:
            tags = list(urltagger.tagURL(item))
            self.assertEqual(len(tags), 1, 'expected one tag for %r' % (item,))
            self.assertEqual(tags[0], tag, 'expected tag %r for %r' % (tag, item))

    def assertNoTag(self, items):
        for item in items:
            self.assertEqual(len(list(urltagger.tagURL(item))), 0)

    def testSearch(self):
        positives = ('http://www.google.com/search?hs=reX&hl=en&lr=&safe=off'
                        '&client=opera&rls=en&q=blotch&btnG=Search',
                     'http://search.yahoo.com/search?p=divmod&sm=Yahoo%21+Search'
                        '&fr=FP-tab-web-t-298&toggle=1&cop=&ei=UTF-8',
                     'http://search.msn.com/results.aspx?q=microsoft&FORM=MSNH&srch_type=0',
                     'http://search.msn.com/encarta/results.aspx?FORM=ENHP&q=',
                     'http://search.msn.com/local/results.aspx?q=d&FORM=QBXR3',
                     'http://search.msn.com/images/results.aspx?FORM=IRXR&q=d%20parow%2C%20western%20cape',
                     'http://video.google.com/videosearch?q=d&btnG=Search+Video',
                     'http://images.google.co.za/images?svnum=10&hl=en&lr=&q=elephants&btnG=Search',
                     'http://clusty.com/search?query=search%engines',
                     'http://www.search.com/search?tag=se.fd.box.main.search&q=foobar')

        self.assertOnlyTag(positives, 'search')

        negatives = ('http://www.google.com/ig',
                     'http://images.google.com',
                     'http://www.yahoo.com/_ylh=X3oDMTEybGQxYTN0BF9TAzI3MTYxNDkEdGV'
                        'zdAN2Mjk4BHRtcGwDdjI5OC1jc3M-/r/3m',
                     'http://images.google.co.za/preferences?q=elephants&hl=en&lr=',
                     'https://adwords.google.com/select/main?cmd=Login&sourceid=AWO&subid=US-ET-ADS&hl=en_US',
                     'http://toolbar.msn.com/?FORM=TLBRFT',
                     'http://www.dogpile.com/info.dogpl/clickit/search?r_aid=BCC09C95F8EA45A9B694D89E8F373700'
                        '&r_eop=2&r_sacop=5&r_spf=0&r_cop=main-title&r_snpp=2&r_spp=3&qqn=n)'
                        '42U%262c&r_coid=239138&rawto=http://www.vh1.com/shows/dyn/flab_to_fab/series.jhtml')

        self.assertNoTag(negatives)

    def testNews(self):
        positives = ('http://www.bloomberg.com/apps/news?pid=10000086&sid=atYe2AWJKC10&refer=latin_america',
                     'http://www.sfgate.com/cgi-bin/article.cgi?f=/n/a/2005/10/24/national/w063847D11.DTL',
                     'http://www.washingtonpost.com/wp-dyn/content/article/2005/10/23/AR2005102301352.html',
                     'http://www.alertnet.org/thenews/newsdesk/L24608596.htm',
                     'http://www.guardian.co.uk/hurricanes2005/story/0,16546,1599592,00.html',
                     'http://www.guardian.co.uk/worldlatest/story/0,1280,-5366049,00.html',
                     'http://www.timesonline.co.uk/article/0,,2-1840842,00.html',
                     'http://www.usatoday.com/news/washington/2005-10-23-miers-senators_x.htm',
                     'http://money.cnn.com/2005/10/24/technology/apple_nano.reut/',
                     'http://edition.cnn.com/2005/WORLD/europe/10/24/poland.coalition.ap/',
                     'http://today.reuters.com/business/newsarticle.aspx?type=ousiv&'
                        'storyID=2005-10-24T030304Z_01_KRA410926_RTRIDST_0_BUSINESSPRO-APPLE-NANO-DC.XML',
                     'http://news.bbc.co.uk/1/hi/entertainment/film/4370742.stm',
                     'http://www.usatoday.com/news/world/iraq/2005-10-24-insurgent-attacks_x.htm',
                     'http://www.usatoday.com/life/people/2005-10-23-spears-site-pics_x.htm?POE=LIFISVA',
                     'http://today.reuters.co.uk/news/newsArticle.aspx?type=topNews&storyID=2005-10-24'
                        'T070435Z_01_KNE425338_RTRUKOC_0_UK-BRITAIN-ATTACK.xml',
                    'http://observer.guardian.co.uk/business/story/0,6903,1598469,00.html',
                    'http://today.reuters.com/news/NewsArticle.aspx?type=topNews&storyID=2005-10-24'
                        'T140129Z_01_MOR420788_RTRUKOC_0_US-WEATHER-WILMA.xml')

        self.assertOnlyTag(positives, 'news')

        negatives = ('http://www.usatoday.com/sports/scores.htm',
                     'http://www.bbc.co.uk/strictlycomedancing/about/strictly_african.shtml',
                     'http://news.bbc.co.uk/1/hi/world/default.stm',
                     'http://news.bbc.co.uk/newswatch/ukfs/hi/default.stm',
                     'http://today.reuters.com/news/default.aspx',
                     'http://today.reuters.com/news/newsChannel.aspx?type=businessNews')

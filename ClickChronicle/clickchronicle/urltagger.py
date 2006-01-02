"""Extremely simple module that relies on regular expressions to classify urls"""
from nevow.url import URL

# mapping of {tag : ((hostname, path_regex), ...)}.  could easily be modified to support
# a hierarchy of tags, but we dont need that yet.  hostnames are tested using
# __contains__, path regexes case insensitively with match().  this could also be changed


_tags = {u'search':[['google',           r'(?:base/)*(?:search|images|videosearch)$'],
                    ['search.yahoo.com', r'search$'],
                    ['clusty.com',       r'search$'],
                    ['search.com',       r'search$'],
                    ['search.msn.com',   r'(?:(?:encarta|local|images|news)/)?results\.aspx$'],
                    ['a9.com',           r'[^\-]']],

         u'news':[['nytimes.com',        r'\d{4}/\d{2}/\d{2}'],
                  ['cnn.com',            r'\d{4}'],
                  ['reuters',            r'\w+/newsarticle\.aspx'],
                  ['alertnet.org',       r'thenews/newsdesk/\w+.htm'],
                  ['news.bbc.co.uk',     r'\d+/([^/]+/)*\d+\.stm'],
                  ['msnbc.msn.com',      r'id'],
                  ['washingtonpost.com', r'wp-dyn/content/article/\d{4}/\d{2}/\d{2}'],
                  ['sfgate.com',         r'cgi-bin/article\.cgi$'],
                  ['sciam.com',          r'article\.cfm'],
                  ['nydailynews.com',    r'\w+/story'],
                  ['bloomberg.com',      r'apps/news$'],
                  ['timesonline.co.uk',  r'article'],
                  ['usatoday.com',       r'(?:\w+/){2,3}\d{4}\-\d{2}\-\d{2}'],
                  ['forbes.com',         r'(?:\w+/){3,4}\d{4}\/\d{2}\/\d{2}\/[^.]+\.html'],
                  ['news.yahoo.com',     r's/\w+/\d{8}'],
                  ['guardian.co.uk',     r'\w+/story/.*?\.htm']]}

def _precompile(tagmap):
    import re

    for (tag, predicates) in tagmap.iteritems():
        for (i, (netloc, pathPattern)) in enumerate(predicates):
            predicates[i][1] = re.compile(pathPattern, re.IGNORECASE)

_precompile(_tags)

def tagURL(url, tagmap=_tags):
    url = URL.fromString(url)
    (netloc, path) = (url.netloc, url.path)
    for (tag, predicates) in tagmap.iteritems():
        for (expected_netloc, pathRegex) in predicates:
            if expected_netloc in netloc and pathRegex.match(path):
                yield tag

import re

phrase = re.compile(r'("[^"]+?")')
minusWord = re.compile(r'\-(\S+)')
minusPhrase = re.compile(r'\-%s' % phrase.pattern)

def parseSearchString(s):
    result = []
    for negRegex in (minusPhrase, minusWord):
        result.extend('NOT %s' % r for r in negRegex.findall(s))
        s = negRegex.sub('', s) 

    result.extend(phrase.findall(s))
    s = phrase.sub('', s)
    result.extend(s.split())
    return result

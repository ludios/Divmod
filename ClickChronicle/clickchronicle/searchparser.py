import re

phrase = re.compile(r'("[^"]+?")', re.U)
minusWord = re.compile(r'\-(\S+)', re.U)
minusPhrase = re.compile(r'\-%s' % phrase.pattern, re.U)

def parseSearchString(s):
    result = []
    for negRegex in (minusPhrase, minusWord):
        result.extend('NOT %s' % r for r in negRegex.findall(s))
        s = negRegex.sub('', s) 

    result.extend(phrase.findall(s))
    s = phrase.sub('', s)
    result.extend(s.split())
    return result

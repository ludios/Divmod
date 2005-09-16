from xapwrap.document import StandardAnalyzer
from math import log

def buildCounts(text):
    sa = StandardAnalyzer()
    toks = sa.tokenize(text)
    unigrams = {}
    bigrams = {}
    count = 0

    prev = None
    for tok in toks:
        count+=1
        if tok in unigrams:
            unigrams[tok]+=1
        else:
            unigrams[tok]=1
        if not prev:
            prev = tok
            continue
        else:
            bigram=(prev, tok)
            if bigram in bigrams:
                bigrams[bigram]+=1
            else:
                bigrams[bigram]=1
            prev = tok
    return count, unigrams, bigrams

def buildMutualInfo(count, unigrams, bigrams):
    mutualInfo = []
    count=float(count)
    for (first, second), pairCount in bigrams.iteritems():
        fCount=unigrams[first]
        fProb=log(fCount/count)
        sCount=unigrams[second]
        sProb=log(sCount/count)
        pairProb=(pairCount/count)
        mi=pairProb - fProb + sProb
        mutualInfo.append((mi, fCount, sCount, pairCount, first, second))
    mutualInfo.sort(lambda a, b: cmp(b[0], a[0]))
    return mutualInfo

def log_l(p, total, k, cols=2, m=4):
    fSum = 0.0
    logTotal = log(total)

    for j in range(0,2):
        if p[j]>0:
            fSum += k[j] * log(p[j]/total)
        elif k[j]>0:
            print 'error something is zero when it should not be'
    return fSum
            
def likelihoodRatio(count, mi):
    mi, fCount, sCount, pairCount, first, second = mi
    cTable = {}
    cTable[(0,0)]=pairCount
    cTable[(0,1)]=fCount - pairCount
    cTable[(1,0)]=sCount - pairCount
    cTable[(1,1)]=count-fCount-sCount+pairCount

    rowSum = [0.0, 0.0]
    colSum = [0.0, 0.0]
    total = 0.0
    
    for i in range(0,2):
        rowSum[i]=0.0
        for j in range(0,2):
            rowSum[i]+=cTable[(i,j)]
            colSum[j]+=cTable[(i,j)]
        total+=rowSum[i]

    fSum = 0.0
    for i in range(0,2):
        fSum += (log_l([cTable[(0,0)], cTable[(i,1)]],rowSum[i],
                       [cTable[(0,0)], cTable[(i,1)]]) -
                log_l(colSum, total, [cTable[(0,0)], cTable[(i,1)]]))
    return fSum * 2
        

if __name__ == '__main__':
    import sys
    str = """speno: The funny thing is, I actually had typed those exact
    words above the cover image, but I took them out before posting to
    let people draw their own conclusions. So now I can say it: I
    agree, it truly is the best cover ever. The O.Reilly designers
    nailed it"""
    count, unigrams, bigrams= buildCounts(str)
    res = buildMutualInfo(count, unigrams, bigrams)
    final = [likelihoodRatio(count, r) for r in res]
    
    for pair in zip(final, res):
        print pair
    

        
        

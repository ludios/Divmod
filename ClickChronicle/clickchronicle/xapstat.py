import xapian

db=xapian.open('xap.index', False)
enq=xapian.Enquire(db)
avLen = db.get_avlength()
print db.get_termfreq('gadget') # num docs in index containing term
print db.get_collection_freq('gadget') # times term occurs in index
numDocs = db.get_doccount()

q=xapian.Query('sony')
enq.set_query(q)
res=enq.get_mset(0,100)

ALLDOCS = {}


def buildDict(doc):
    tlb=doc.termlist_begin()
    tle=doc.termlist_end()

    thisDoc = {}
    
    count = 0
    while tlb != tle:
        term = tlb.get_term()
        occ = tlb.get_wdf()
        count += occ
        thisDoc[term]=occ
        ALLDOCS[term]=db.get_collection_freq(term)
        #L.append((tlb.get_term(), # string
        #          tlb.get_termfreq(), # num docs containing term
        #          tlb.get_wdf())) # num occurences of term in this doc
        tlb.next()
    return (count, thisDoc)

docCounts = [buildDict(dc[4]) for dc in res]
# print L
#print thisDoc['gadget']
from math import sqrt

def z_values(text, overall, n_t, n_o):
    """calculate the z values for each word in the given text relative to the overall text"""
    
    t = text
    o = overall
    n_t = len(text)
    n_o = numDocs * avLen
    
    result = {}

    for word in t:
        p_hat = float(t[word]) / n_t
        p_0 = float(o[word]) / n_o
        
        z = (p_hat - p_0) / sqrt((p_0 * (1 - p_0)) / n_t)
    
        result[word] = z

    return result

res =  [z_values(thisDoc, ALLDOCS, count, numDocs * avLen) for count, thisDoc in docCounts]

def filter_z(z_values, threshold):
    """return only those items that meet the given z value threshold"""

    sign = int(abs(threshold) / threshold)
    l = [(i, z_values[i]) for i in z_values if cmp(z_values[i], threshold) == sign]
    l.sort(lambda a, b: -sign * cmp(a[1], b[1]))
    return l

for r in res:
    unusually_frequent = filter_z(r, 4)
    unusually_rare = filter_z(r, -2)
    print '###############'
    print unusually_frequent[:25]
    print '***************'
    print unusually_rare

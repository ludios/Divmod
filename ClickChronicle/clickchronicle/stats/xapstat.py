import xapian

db=xapian.open('xap.index', False)
enq=xapian.Enquire(db)
avLen = db.get_avlength()
numDocs = db.get_doccount()
#print db.get_termfreq('the') # num docs in index containing term
#print db.get_collection_freq('the') # times term occurs in index
print 'total words: ', avLen * numDocs


ALLDOCS = {}

def buildDict(doc):
    docId = doc[0]
    doc=doc[4]
    title = doc.get_value(2)
    url = doc.get_value(6)
    docLen = db.get_doclength(docId)
    tlb=doc.termlist_begin()
    tle=doc.termlist_end()

    thisDoc = {}
    
    while tlb != tle:
        term = tlb.get_term()
        occ = tlb.get_wdf()
        thisDoc[term]=occ
        ALLDOCS[term]=db.get_collection_freq(term)
        #L.append((tlb.get_term(), # string
        #          tlb.get_termfreq(), # num docs containing term
        #          tlb.get_wdf())) # num occurences of term in this doc
        tlb.next()
    #print 'the for docId %s: %s out of %s' % (docId, thisDoc['the'], docLen)
    return (docLen, thisDoc, title, url)

q=xapian.Query('the')
enq.set_query(q)
res=enq.get_mset(0,100)

docCounts = [buildDict(dc) for dc in res]
# print L
#print thisDoc['gadget']
from math import sqrt

def z_values(text, overall, n_t, n_o, ignore, title, url):
    """calculate the z values for each word in the given text relative to the overall text"""
    t = text
    o = overall
            
    result = {}
    for word in t:
        if word not in ignore:
            p_hat = float(t[word]) / n_t
            p_0 = float(o[word]) / n_o
            z = (p_hat - p_0) / sqrt((p_0 * (1 - p_0)) / n_t)
            result[word] = z
    return result, title, url

# Ignore the most common tersm
sAllDocs = ALLDOCS.items()
sAllDocs.sort(lambda a, b: cmp(b[1], a[1]))
cut = int(len(ALLDOCS)*.005)
#print len(ALLDOCS), cut, sAllDocs[:cut]
ignore = dict(sAllDocs[:cut])
#print ignore
res =  [z_values(thisDoc, ALLDOCS, count, numDocs * avLen, ignore, title, url) for count, thisDoc, title, url in docCounts]

def filter_z(z_values, threshold):
    """return only those items that meet the given z value threshold"""

    sign = int(abs(threshold) / threshold)
    l = [(i, z_values[i]) for i in z_values if cmp(z_values[i], threshold) == sign]
    l.sort(lambda a, b: -sign * cmp(a[1], b[1]))
    return l

for r, title, url in res:
    print '###############'
    print title
    print url
    unusually_frequent = filter_z(r, 7)
    unusually_rare = filter_z(r, -3)
    print unusually_frequent[:25]
    print '--'
    print unusually_rare

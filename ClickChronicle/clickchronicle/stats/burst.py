from math import log

class Burst:
    def __init__(self):
        self.states = []
        self.gamma = None
        self.statesUsed = []
        self.data = []

    def setState(self, lamb, index=None):
        self.states.append(lamb)

    def generateStates(self, count, rate, sigma):
        for i in range(count):
            self.setState(rate*(sigma**i))

    def setGamma(self, gamma):
        self.gamma = gamma

    def setData(self, gapSpace):
        self.data=gapSpace
        self.statesUsed=[0 for i in range(len(gapSpace))]
                
    def process(self, n=11):
        self.calcCost(n)

    def calcCost(self, pos):
        #print 'calc', pos
        
        if pos == 0:
            self.statesUsed[0]=0
            return 0,0
        
        numStates = len(self.states)
        minCost = 99999.0
        state = -1
        costImprove = True

        for tryState in range(numStates):
            if costImprove is False:
                break
            newState, newCost = self.calcCost(pos-1)
            trans = self.transition(newState, tryState, self.data[pos])
            alignment = -1 * log(self.func(self.states[tryState], self.data[pos]))
            cost = alignment + newCost + trans
            #print "%s: %s -> %s = a:%s prev:%s +trans: %s" % (pos, tryState, cost, alignment, newCost, trans)
            #print 'cm', cost, minCost
            if cost < minCost:
                #print 'cost < minCost'
                minCost = cost
                state = tryState
                self.statesUsed[pos]=state
                #self.statesUsed.append(state)
            else:
                #print 'ci set to False'
                costImprove = False
        return state, minCost

    def transition(self, prev, curr, datum):
        #print "trans:", prev, curr, pos
        if prev >= curr:
            return 0
        else:
            return self.gamma * (curr - prev) * log(datum)
            
    def func(self, lamba, x):
        e=2.718
        value = lamba * e ** (lamba * x * -1.0)
        #print 'func', value, lamba, x
        return value
    
    def getStatesUsed(self):
        return self.statesUsed

if __name__ == '__main__':
    data = [9,9,9,9,9,6,7,8,9,9,2,2,2,2,9,9,9,9,1,1,9,9,9,9,9,9]
    b=Burst()
    b.generateStates(5,.111,2)
    b.setGamma(.5)
    b.setData(data)
    n = 13
    b.process(n)
    statesUsed=b.getStatesUsed()
    print 'data      ', data
    print 'data %s  %s', n, data[:n]
    print 'statesUsed', statesUsed

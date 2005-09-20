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
        lamba=self.states
        stateCount = len(lamba)
        if pos == 0:
            self.statesUsed[0]=0
            return 0,0

        minCosts = 99999.0
        state = -1
        gap_space = self.data
        costImprove = True

        for tryState in range(stateCount):
            if not costImprove:
                break
            newState, newCosts =self.calcCost(pos-1)
            trans = self.transition(newState, tryState, gap_space[pos])
            pc = newCosts
            alignment = -1 * log(self.func(lamba[tryState], gap_space[pos]))
            cost = alignment + pc + trans
            #print "%s: %s -> %s = a:%s prev:%s +trans: %s" % (pos, tryState, cost, alignment, pc, trans)
            #print 'cm', cost, minCosts
            if cost < minCosts:
                #print 'cost < minCosts'
                minCosts = cost
                state = tryState
                self.statesUsed[pos]=state
                #self.statesUsed.append(state)
            else:
                #print 'ci set to False'
                costImprove = False
        return state, minCosts

    def transition(self, prev, curr, pos):
        #print "trans:", prev, curr, pos
        if prev >= curr:
            return 0
        else:
            return self.gamma * (curr - prev) * log(pos)
            
    def func(self, lamba, x):
        e=2.718
        value = lamba * e ** (lamba * x * -1.0)
        #print 'func', value, lamba, x
        return value
    
    def getStatesUsed(self):
        return self.statesUsed

if __name__ == '__main__':
    data = [9,9,10,10,14,5,7,5,9,9,9,9,9,9,10,10,14,5,2,2,2,2,7,5,9,9,9,9]
    b=Burst()
    b.generateStates(3,.111,2)
    b.setGamma(.5)
    b.setData(data)
    b.process(30)
    statesUsed=b.getStatesUsed()
    print 'data      ', data
    print 'statesUsed', statesUsed

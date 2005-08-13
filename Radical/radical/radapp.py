
import random

from zope.interface import implements

from twisted.plugin import IPlugin
from twisted.python.components import registerAdapter
from twisted.python import util

from nevow import rend, loaders, livepage, flat, static, json, tags as T

from axiom import store
from axiom.item import Item
from axiom.attributes import reference, integer, inmemory

from xmantissa.ixmantissa import INavigableFragment, INavigableElement, ISessionlessSiteRootPlugin, ISiteRootPlugin
from xmantissa import webnav, website

VOID, MOUNTAIN, GRASS, WATER, FOREST, DESERT = range(6)
TERRAIN_TYPES = (MOUNTAIN, GRASS, WATER, FOREST, DESERT)

TERRAIN_NAMES = {
    MOUNTAIN: 'mountain',
    GRASS: 'grass',
    FOREST: 'forest',
    WATER: 'water',
    DESERT: 'desert',
    VOID: 'void',
    }

VIEWPORT_X = 8
VIEWPORT_Y = 8

class RadicalWorld(Item, website.PrefixURLMixin):
    implements(ISessionlessSiteRootPlugin)

    schemaVersion = 1
    typeName = 'radical_world'

    seed = integer()

    terrain = inmemory()
    players = inmemory()

    prefixURL = 'static/radical'

    width = integer(default=100)
    height = integer(default=100)

    def install(self):
        self.store.powerUp(self, ISessionlessSiteRootPlugin)

    def getTerrain(self):
        if not hasattr(self, 'terrain'):
            rnd = random.Random()
            rnd.seed(self.seed)
            self.terrain = [rnd.choice(TERRAIN_TYPES) for n in range(self.width) for m in range(self.height)]
        return self.terrain

    def getTerrainAt(self, x, y):
        t = self.getTerrain()
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return TERRAIN_NAMES[VOID]
        return TERRAIN_NAMES[t[y * self.width + x]]

    def addPlayer(self, player):
        if not hasattr(self, 'players'):
            self.players = []
        self.players.append(player)
        for p in self.players:
            if p is not player:
                player.observeMovement(p, (p.original.posX, p.original.posY))

    def removePlayer(self, player):
        self.players.remove(player)
        for p in self.players:
            p.observeDisappearance(player)

    def playerMoved(self, who, where):
        for p in self.players:
            if p is not who:
                p.observeMovement(who, where)

    def playerMessage(self, who, what):
        for p in self.players:
            if p is not who:
                p.observeMessage(who, what)


    # ISessionlessSiteRootPlugin, via PrefixURLMixin
    def createResource(self):
        return static.File(util.sibpath(__file__, 'static'))


class RadicalApplication(Item, website.PrefixURLMixin):
    implements(INavigableElement)

    schemaVersion = 1
    typeName = 'radical_application'

    character = reference()

    prefixURL = 'private/radical'

    def install(self):
        self.store.powerUp(self, INavigableElement)
        self.character = RadicalCharacter(store=self.store)

    def getTabs(self):
        return [webnav.Tab('Games', self.storeID, 0.0,
                           [webnav.Tab('Radical',
                                       self.character.storeID,
                                       0.0)],
                           authoritative=False)]



class RadicalCharacter(Item):
    schemaVersion = 1
    typeName = 'radical_character'

    hitpoints = integer(default=1)
    posX = integer(default=10)
    posY = integer(default=10)


theMap = livepage.js.theMap

def _pickDisplayCoordinate(pos, viewport, max):
    if pos <= viewport / 2:
        return pos
    if pos > max - viewport / 2:
        return viewport - (max - pos)
    return viewport / 2

class RadicalGame(rend.Fragment):
    implements(INavigableFragment)

    live = True
    fragmentName = 'radical-map'

    charImage = 'player'

    _charCounter = 0

    def head(self):
        return [
            T.script(language='javascript', src='/static/radical/ambulation.js'),
            T.script(language='javascript', src='/static/radical/json.js'),
            ]

    def newCharacter(self, image):
        self._charCounter += 1
        self._charImages[self._charCounter] = image
        return self._charCounter

    def getWorld(self):
        for world in self.original.store.parent.query(RadicalWorld):
            return world
        raise RuntimeError("No world found")

    def _closed(self, ignored):
        self.world.removePlayer(self)

    def goingLive(self, ctx, client):
        self.client = client
        self.world = self.getWorld()

        self._charImages = {}
        self.me = self.newCharacter(self.charImage)
        self._otherPeople = {self: self.me}

        self.dispX = _pickDisplayCoordinate(self.original.posX, VIEWPORT_X, self.world.width)
        self.dispY = _pickDisplayCoordinate(self.original.posY, VIEWPORT_Y, self.world.height)

        self.sendCompleteTerrain()
        self.world.addPlayer(self)
        client.notifyOnClose().addBoth(self._closed)

        print 'I am at', (self.original.posX, self.original.posY), 'and viewport selected was', (self.dispX, self.dispY)
        self.world.playerMoved(self, (self.original.posX, self.original.posY))


    def inRange(self, other):
        baseX = self.original.posX - self.dispX
        baseY = self.original.posY - self.dispY
        return (
            (baseX <= other.original.posX < baseX + VIEWPORT_X) and
            (baseY <= other.original.posY < baseY + VIEWPORT_Y))

    def observeMovement(self, who, where):
        if self.inRange(who):
            if who not in self._otherPeople:
                self._otherPeople[who] = self.newCharacter(self.charImage)
            row = who.original.posX - (self.original.posX - self.dispX)
            col = who.original.posY - (self.original.posY - self.dispY)
            self.client.send(self.moveCharacter(self._otherPeople[who], row, col))
        else:
            if who in self._otherPeople:
                self.client.send(self.eraseCharacter(self._otherPeople.pop(who)))

    def observeMessage(self, who, what):
        if self.inRange(who) and who in self._otherPeople:
            self.client.send(self.appendMessage(who, what))

    def observeDisappearance(self, who):
        if self.inRange(who) and who in self._otherPeople:
            self.client.send(self.eraseCharacter(self._otherPeople.pop(who)))

    def appendMessage(self, who, what):
        return livepage.js.appendMessage(self._otherPeople[who], what)

    def eraseCharacter(self, id):
        return livepage.js.eraseCharacter(id)

    def moveCharacter(self, id, row, col):
        return livepage.js.moveCharacter(id, row, col, self._charImages[id])

    def updateMyPosition(self):
        return self.moveCharacter(self.me, self.dispX, self.dispY)

    def sendCompleteTerrain(self):
        """
        Send an entire screen's worth of terrain to the client,
        centered at the client's current position.
        """
        ch = self.original
        visTerr = [[None] * VIEWPORT_Y for n in range(VIEWPORT_X)]
        xBase = ch.posX - self.dispX
        yBase = ch.posY - self.dispY
        for visY in range(VIEWPORT_Y):
            yPos = yBase + visY
            for visX in range(VIEWPORT_X):
                xPos = xBase + visX
                visTerr[visX][visY] = self.world.getTerrainAt(xPos, yPos)

        self.client.send([
                livepage.js.initializeMap(livepage.js(json.serialize(visTerr))),
                livepage.eol,
                self.moveCharacter(self.me, self.dispX, self.dispY),
                livepage.eol,
                ])


    def _vertScroll(self, func):
        ch = self.original
        allTerr = self.world.getTerrain()
        visTerr = [None] * VIEWPORT_X
        base = ch.posX - self.dispX
        for visX in xrange(base, base + VIEWPORT_X):
            visTerr[visX - base] = self.world.getTerrainAt(visX, ch.posY)
        return func(livepage.js(json.serialize(visTerr)))


    def scrollDown(self):
        return self._vertScroll(theMap.insertTopRow)


    def scrollUp(self):
        return self._vertScroll(theMap.insertBottomRow)


    def _horizScroll(self, func  ):
        ch = self.original
        allTerr = self.world.getTerrain()
        visTerr = [None] * VIEWPORT_Y
        base = ch.posY - self.dispY
        for visY in range(base, base + VIEWPORT_Y):
            visTerr[visY - base] = self.world.getTerrainAt(ch.posX, visY)
        return func(livepage.js(json.serialize(visTerr)))


    def scrollLeft(self):
        return self._horizScroll(theMap.insertRightColumn)


    def scrollRight(self):
        return self._horizScroll(theMap.insertLeftColumn)


    message = ''
    def sendMessage(self, message):
        self.world.playerMessage(self, message)
        self.observeMessage(self, message)


    def handle_document(self, ctx, doc):
        file('document', 'w').write(doc)


    def handle_keyPress(self, ctx, which, alt, ctrl, meta, shift):
        alt = alt == 'true'
        ctrl = ctrl == 'true'
        meta = meta == 'true'
        shift = shift == 'true'
        print which, alt and 'A' or '.', ctrl and 'C' or '.', meta and 'M' or '.', shift and 'S' or '.'
        print self.dispX, self.dispY
        print self.original.posX, self.original.posY


    def handle_sendMessage(self, ctx, message):
        self.sendMessage(message)


    def handle_upArrow(self, ctx):
        if self.dispY > 0:
            self.dispY -= 1
            self.original.posY -= 1
            yield self.updateMyPosition()
        elif self.original.posY > 0:
            self.original.posY -= 1
            yield self.scrollDown()
        else:
            return
        self.world.playerMoved(self, (self.original.posX, self.original.posY))


    def handle_downArrow(self, ctx):
        if self.dispY < VIEWPORT_Y - 1:
            self.dispY += 1
            self.original.posY += 1
            yield self.updateMyPosition()
        elif self.original.posY < self.world.height - 1:
            self.original.posY += 1
            yield self.scrollUp()
        else:
            return
        self.world.playerMoved(self, (self.original.posX, self.original.posY))


    def handle_leftArrow(self, ctx):
        if self.dispX > 0:
            self.dispX -= 1
            self.original.posX -= 1
            yield self.updateMyPosition()
        elif self.original.posX > 0:
            self.original.posX -= 1
            yield self.scrollRight()
        else:
            return
        self.world.playerMoved(self, (self.original.posX, self.original.posY))


    def handle_rightArrow(self, ctx):
        if self.dispX < VIEWPORT_X - 1:
            self.dispX += 1
            self.original.posX += 1
            yield self.updateMyPosition()
        elif self.original.posX < self.world.width - 1:
            self.original.posX += 1
            yield self.scrollLeft()
        else:
            return
        self.world.playerMoved(self, (self.original.posX, self.original.posY))


registerAdapter(RadicalGame, RadicalCharacter, INavigableFragment)

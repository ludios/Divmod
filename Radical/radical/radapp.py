
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

VIEWPORT_X = 4
VIEWPORT_Y = 4

class RadicalWorld(Item, website.PrefixURLMixin):
    implements(ISessionlessSiteRootPlugin)

    schemaVersion = 1
    typeName = 'radical_world'

    seed = integer()

    terrain = inmemory()

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
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return TERRAIN_NAMES[VOID]
        return TERRAIN_NAMES[self.getTerrain()[y * self.width + x]]

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


class RadicalGame(rend.Fragment):
    live = True
    fragmentName = 'radical-game'
    docFactory = loaders.stan([
            T.script(language='javascript', src='/static/radical/ambulation.js'),
            T.div(id='map-node', onkeypress=livepage.js.server.handle('keypress', livepage.js.event)),
            ])

    dispX = VIEWPORT_X / 2
    dispY = VIEWPORT_Y / 2

    charImage = 'player'

    _charCounter = 0

    def getWorld(self):
        for world in self.original.store.parent.query(RadicalWorld):
            return world
        raise RuntimeError("No world found")

    def goingLive(self, ctx, client):
        self._charImages = {}
        self.client = client
        self.world = self.getWorld()
        self.sendCompleteTerrain()

    def newCharacter(self, image):
        self._charCounter += 1
        self._charImages[self._charCounter] = image
        return self._charCounter

    def moveCharacter(self, id, row, col):
        return livepage.js.moveCharacter(id, row, col, self._charImages[id])

    def updateMyPosition(self):
        return self.moveCharacter(self.me, self.dispY, self.dispX)

    def sendCompleteTerrain(self):
        """
        Send an entire screen's worth of terrain to the client,
        centered at the client's current position.
        """
        ch = self.original
        def send():
            visTerr = [[None] * VIEWPORT_Y for n in range(VIEWPORT_X)]
            xBase = ch.posX - (VIEWPORT_X / 2)
            yBase = ch.posY - (VIEWPORT_Y / 2)
            for visY in range(VIEWPORT_Y):
                yPos = yBase + visY
                for visX in range(VIEWPORT_X):
                    xPos = xBase + visX
                    visTerr[visX][visY] = self.world.getTerrainAt(xPos, yPos)

            self.me = self.newCharacter(self.charImage)

            self.client.send([
                    livepage.js.initializeMap(livepage.js(json.serialize(visTerr))),
                    livepage.eol,
                    self.moveCharacter(self.me, self.dispY, self.dispX),
                    livepage.eol,
                    ])

        from twisted.internet import reactor
        reactor.callLater(0.1, send)

    def _vertScroll(self, func):
        ch = self.original
        allTerr = self.world.getTerrain()
        visTerr = [None] * VIEWPORT_X
        base = ch.posX - self.dispX
        for visX in xrange(base, base + VIEWPORT_X):
            visTerr[visX - base] = self.world.getTerrainAt(visX, ch.posY)
        return func(livepage.js(json.serialize(visTerr)))

    def scrollDown(self):
        return self._vertScroll(livepage.js.insertTopRow)

    def scrollUp(self):
        return self._vertScroll(livepage.js.insertBottomRow)

    def _horizScroll(self, func  ):
        ch = self.original
        allTerr = self.world.getTerrain()
        visTerr = [None] * VIEWPORT_Y
        base = ch.posY - self.dispY
        for visY in range(base, base + VIEWPORT_Y):
            visTerr[visY - base] = self.world.getTerrainAt(ch.posX, visY)
        return func(livepage.js(json.serialize(visTerr)))


    def scrollLeft(self):
        return self._horizScroll(livepage.js.insertLeftColumn)

    def scrollRight(self):
        return self._horizScroll(livepage.js.insertRightColumn)

    def handle_keyPress(self, ctx, which, alt, ctrl, meta, shift):
        print self.dispX, self.dispY
        print self.original.posX, self.original.posY

    def handle_upArrow(self, ctx):
        if self.dispY > 0:
            self.dispY -= 1
            self.original.posY -= 1
            yield self.updateMyPosition()
        else:
            if self.original.posY > 0:
                self.original.posY -= 1
                yield self.scrollDown()


    def handle_downArrow(self, ctx):
        if self.dispY < VIEWPORT_Y - 1:
            self.dispY += 1
            self.original.posY += 1
            yield self.updateMyPosition()
        else:
            if self.original.posY < self.world.height - 1:
                self.original.posY += 1
                yield self.scrollUp()


    def handle_leftArrow(self, ctx):
        if self.dispX > 0:
            self.dispX -= 1
            self.original.posX -= 1
            yield self.updateMyPosition()
        else:
            if self.original.posX > 0:
                self.original.posX -= 1
                yield self.scrollRight()


    def handle_rightArrow(self, ctx):
        if self.dispX < VIEWPORT_X - 1:
            self.dispX += 1
            self.original.posX += 1
            yield self.updateMyPosition()
        else:
            if self.original.posX < self.world.width - 1:
                self.original.posX += 1
                yield self.scrollLeft()


registerAdapter(RadicalGame, RadicalCharacter, INavigableFragment)

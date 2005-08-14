
import random

from zope.interface import implements, Interface

from twisted.plugin import IPlugin
from twisted.python.components import registerAdapter
from twisted.python import util

from nevow import rend, loaders, livepage, flat, static, json, tags as T

from axiom import store, extime
from axiom.item import Item
from axiom.attributes import reference, integer, text, timestamp, inmemory

from xmantissa.ixmantissa import INavigableFragment, INavigableElement, ISessionlessSiteRootPlugin, ISiteRootPlugin
from xmantissa import webnav, website

VOID, MOUNTAIN, GRASS, WATER, FOREST, DESERT = range(6)
TERRAIN_TYPES = (MOUNTAIN, GRASS, WATER, FOREST, DESERT)

TERRAIN_NAMES = {
    MOUNTAIN: u'mountain',
    GRASS: u'grass',
    FOREST: u'forest',
    WATER: u'water',
    DESERT: u'desert',
    VOID: u'void',
    }

VIEWPORT_X = 8
VIEWPORT_Y = 8

class Location(object):
    def __init__(self, terrain, contents):
        self.terrain = terrain
        self.contents = contents

    def getTerrain(self):
        return TERRAIN_NAMES[self.terrain]

    def getObjects(self):
        return self.contents


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

        sword = RadicalObject.create(self.store, u'sword')
        sword.powerUp(LocationComponent(store=self.store, x=15, y=15), ILocated)

    def getLocationMatrix(self):
        if not hasattr(self, 'terrain'):
            rnd = random.Random()
            rnd.seed(self.seed)
            self.terrain = [Location(rnd.choice(TERRAIN_TYPES), [])
                            for n in range(self.width)
                            for m in range(self.height)]

            for obj in self.store.query(RadicalObject):
                loc = ILocated(obj, None)
                if loc is not None:
                    self.getLocationAt(loc.x, loc.y).contents.append(obj)
        return self.terrain


    def getLocationAt(self, x, y):
        t = self.getLocationMatrix()
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            raise ValueError("Terrain out of bounds")
        return t[y * self.width + x]

    def addPlayer(self, player):
        if not hasattr(self, 'players'):
            self.players = []
        self.players.append(player)
        for p in self.players:
            if p is not player:
                loc = ILocated(p.original)
                player.observeMovement(p, (loc.x, loc.y))

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
        self.character = RadicalCharacter.create(self.store, 10, 10, u'player')

    def getTabs(self):
        return [webnav.Tab('Games', self.storeID, 0.0,
                           [webnav.Tab('Radical',
                                       self.character.storeID,
                                       0.0)],
                           authoritative=False)]



class ILocated(Interface):
    pass

class IVisible(Interface):
    pass

class ICarryable(Interface):
    pass


class VisibilityComponent(Item):
    typeName = 'radical_visibility_component'
    schemaVersion = 1

    image = text()


class LocationComponent(Item):
    typeName = 'radical_location_component'
    schemaVersion = 1

    x = integer(default=10)
    y = integer(default=10)


class CarriedComponent(Item):
    typeName = 'radical_carried_component'
    schemaVersion = 1

    carriedBy = reference()


class RadicalCharacter(Item):
    schemaVersion = 1
    typeName = 'radical_character'

    hitpoints = integer(default=1)

    def create(cls, store, x, y, image):
        o = cls(store=store)
        o.powerUp(LocationComponent(store=store, x=x, y=y), ILocated)
        o.powerUp(VisibilityComponent(store=store, image=image), IVisible)
        return o
    create = classmethod(create)


class RadicalObject(Item):
    schemaVersion = 1
    typeName = 'radical_object'

    created = timestamp()

    def create(cls, store, image):
        o = cls(store=store, created=extime.Time())
        o.powerUp(VisibilityComponent(store=store, image=image), IVisible)
        return o
    create = classmethod(create)


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
        self.me = self.newCharacter(IVisible(self.original).image)
        self._otherPeople = {self: self.me}

        loc = ILocated(self.original)

        self.dispX = _pickDisplayCoordinate(loc.x, VIEWPORT_X, self.world.width)
        self.dispY = _pickDisplayCoordinate(loc.y, VIEWPORT_Y, self.world.height)

        self.sendCompleteTerrain()
        self.world.addPlayer(self)
        client.notifyOnClose().addBoth(self._closed)

        print 'I am at', (loc.x, loc.y), 'and viewport selected was', (self.dispX, self.dispY)
        self.world.playerMoved(self, (loc.x, loc.y))


    def inRange(self, other):
        loc = ILocated(self.original)
        oloc = ILocated(other.original)

        baseX = loc.x - self.dispX
        baseY = loc.y - self.dispY
        return (
            (baseX <= oloc.x < baseX + VIEWPORT_X) and
            (baseY <= oloc.y < baseY + VIEWPORT_Y))

    def observeMovement(self, who, where):
        loc = ILocated(self.original)
        wloc = ILocated(who.original)

        if self.inRange(who):
            if who not in self._otherPeople:
                self._otherPeople[who] = self.newCharacter(IVisible(who.original).image)
            row = wloc.x - (loc.x - self.dispX)
            col = wloc.y - (loc.y - self.dispY)
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
        return livepage.js.appendMessage(self._otherPeople[who], what), livepage.eol

    def eraseCharacter(self, id):
        return livepage.js.eraseCharacter(id)

    def moveCharacter(self, id, row, col):
        return livepage.js.moveCharacter(id, row, col, self._charImages[id]), livepage.eol

    def updateMyPosition(self):
        return self.moveCharacter(self.me, self.dispX, self.dispY)

    def sendCompleteTerrain(self):
        """
        Send an entire screen's worth of terrain to the client,
        centered at the client's current position.
        """
        loc = ILocated(self.original)
        visTerr = [[None] * VIEWPORT_Y for n in range(VIEWPORT_X)]
        xBase = loc.x - self.dispX
        yBase = loc.y - self.dispY
        for visY in range(VIEWPORT_Y):
            yPos = yBase + visY
            for visX in range(VIEWPORT_X):
                xPos = xBase + visX
                loc = self.world.getLocationAt(xPos, yPos)
                visTerr[visX][visY] = loc.getTerrain()

        self.client.send([
                livepage.js.initializeMap(livepage.js(json.serialize(visTerr))),
                livepage.eol,
                self.moveCharacter(self.me, self.dispX, self.dispY),
                livepage.eol,
                ])


    def _vertScroll(self, func, row):
        loc = ILocated(self.original)
        base = loc.x - self.dispX
        visTerr = []
        visObjs = []
        for visX in xrange(base, base + VIEWPORT_X):
            location = self.world.getLocationAt(visX, row)
            visTerr.append(location.getTerrain())
            visObjs.append([IVisible(o).image for o in location.getObjects()])

        return func(
            livepage.js(json.serialize(visTerr)),
            livepage.js(json.serialize(visObjs))), livepage.eol

    def scrollDown(self):
        loc = ILocated(self.original)
        return self._vertScroll(theMap.insertTopRow, loc.y - 1 - self.dispY)


    def scrollUp(self):
        loc = ILocated(self.original)
        return self._vertScroll(theMap.insertBottomRow, loc.y + 1 + (VIEWPORT_Y - self.dispY))


    def _horizScroll(self, func):
        loc = ILocated(self.original)
        base = loc.y - self.dispY
        visTerr = []
        visObjs = []
        for visY in range(base, base + VIEWPORT_Y):
            location = self.world.getLocationAt(loc.x, visY)
            visTerr.append(location.getTerrain())
            visObjs.append([IVisible(o).image for o in location.getObjects()])

        return func(
            livepage.js(json.serialize(visTerr)),
            livepage.js(json.serialize(visObjs))), livepage.eol


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
        loc = ILocated(self.original)
        print 'Display', self.dispX, self.dispY
        print 'Actual', loc.x, loc.y


    def handle_sendMessage(self, ctx, message):
        self.sendMessage(message)


    def handle_upArrow(self, ctx, ctrl):
        ctrl = ctrl == 'true'
        if ctrl:
            return self.tryScrollUp()
        else:
            return self.moveUp()

    def moveUp(self):
        loc = ILocated(self.original)

        if self.dispY > 0:
            self.dispY -= 1
            loc.y -= 1
            yield self.updateMyPosition()
        elif loc.y > 0:
            yield self.scrollDown()
            loc.y -= 1
        else:
            return

        self.world.playerMoved(self, (loc.x, loc.y))


    def tryScrollUp(self):
        if self.dispY < VIEWPORT_Y - 1:
            self.dispY += 1
            yield self.scrollDown()
            yield self.updateMyPosition()


    def handle_downArrow(self, ctx, ctrl):
        ctrl = ctrl == 'true'
        if ctrl:
            return self.tryScrollDown()
        else:
            return self.moveDown()

    def moveDown(self):
        loc = ILocated(self.original)

        if self.dispY < VIEWPORT_Y - 1:
            self.dispY += 1
            loc.y += 1
            yield self.updateMyPosition()
        elif loc.y < self.world.height - 1:
            yield self.scrollUp()
            loc.y += 1
        else:
            return
        self.world.playerMoved(self, (loc.x, loc.y))


    def tryScrollDown(self):
        if self.dispY > 0:
            self.dispY -= 1
            yield self.scrollUp()
            yield self.updateMyPosition()


    def handle_leftArrow(self, ctx, ctrl):
        loc = ILocated(self.original)
        if self.dispX > 0:
            self.dispX -= 1
            loc.x -= 1
            yield self.updateMyPosition()
        elif loc.x > 0:
            loc.x -= 1
            yield self.scrollRight()
        else:
            return
        self.world.playerMoved(self, (loc.x, loc.y))


    def handle_rightArrow(self, ctx, ctrl):
        loc = ILocated(self.original)
        if self.dispX < VIEWPORT_X - 1:
            self.dispX += 1
            loc.x += 1
            yield self.updateMyPosition()
        elif loc.x < self.world.width - 1:
            loc.x += 1
            yield self.scrollLeft()
        else:
            return
        self.world.playerMoved(self, (loc.x, loc.y))


registerAdapter(RadicalGame, RadicalCharacter, INavigableFragment)

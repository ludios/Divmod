
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

MOUNTAIN, GRASS = range(2)
TERRAIN_TYPES = (MOUNTAIN, GRASS)

TERRAIN_NAMES = {
    MOUNTAIN: 'mountain',
    GRASS: 'grass',
    }


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
        if not hasattr(self, 'world'):
            rnd = random.Random()
            rnd.seed(self.seed)
            self.terrain = [rnd.choice(TERRAIN_TYPES) for n in range(self.width) for m in range(self.height)]
        return self.terrain

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

    def getWorld(self):
        for world in self.original.store.parent.query(RadicalWorld):
            return world
        raise RuntimeError("No world found")

    def goingLive(self, ctx, client):
        self.client = client
        self.world = self.getWorld()
        self.sendCompleteTerrain()

    def sendCompleteTerrain(self):
        """
        Send an entire screen's worth of terrain to the client,
        centered at the client's current position.
        """
        ch = self.original
        def send():
            allTerr = self.world.getTerrain()
            visTerr = [[None] * 8 for n in range(8)]
            xBase = ch.posX - 4
            yBase = ch.posY - 4
            for visY in range(8):
                for visX in range(8):
                    visTerr[visX][visY] = TERRAIN_NAMES[allTerr[(yBase + visY) * self.world.width + (xBase + visX)]]
            self.client.send(livepage.js.initializeMap(livepage.js(json.serialize(visTerr))))

        from twisted.internet import reactor
        reactor.callLater(1, send)


    def handle_keyPress(self, ctx, which, alt, ctrl, meta, shift):
        print 'key', repr(which), alt, ctrl, meta, shift

    def handle_upArrow(self, ctx):
        ch = self.original
        if ch.posY > 4:
            ch.posY -= 1;
            allTerr = self.world.getTerrain()
            visTerr = [None] * 8
            for visX in range(8):
                visTerr[visX] = TERRAIN_NAMES[allTerr[(ch.posY - 4) * self.world.width + visX]]
            print 'Top inserting', visTerr
            return livepage.js.insertTopRow(livepage.js(json.serialize(visTerr)))

        return livepage.js.alert('You are at the edge of the world!')


    def handle_downArrow(self, ctx):
        ch = self.original
        if ch.posY < len(self.world.getTerrain()) - 4:
            ch.posY += 1;
            allTerr = self.world.getTerrain()
            visTerr = [None] * 8
            for visX in range(8):
                visTerr[visX] = TERRAIN_NAMES[allTerr[(ch.posY + 4) * self.world.width + visX]]
            print 'Bottom inserting', visTerr
            return livepage.js.insertBottomRow(livepage.js(json.serialize(visTerr)))

        return livepage.js.alert('You are at the edge of the world!')


    def handle_leftArrow(self, ctx):
        pass

    def handle_rightArrow(self, ctx):
        pass

registerAdapter(RadicalGame, RadicalCharacter, INavigableFragment)

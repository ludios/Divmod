
import random

from zope.interface import implements

from twisted.plugin import IPlugin
from twisted.python.components import registerAdapter
from twisted.python import util

from nevow import rend, loaders, livepage, flat, static, tags as T

from axiom import store
from axiom.item import Item
from axiom.attributes import reference, integer, inmemory

from xmantissa.ixmantissa import INavigableFragment, INavigableElement, ISessionlessSiteRootPlugin, ISiteRootPlugin
from xmantissa import webnav, website

TERRAIN_TYPES = ('mountain', 'grass')


class RadicalWorld(Item, website.PrefixURLMixin):
    implements(ISessionlessSiteRootPlugin)

    schemaVersion = 1
    typeName = 'radical_world'

    seed = integer()

    world = inmemory()

    prefixURL = 'static/radical'

    def install(self):
        self.store.powerUp(self, ISessionlessSiteRootPlugin)

    def getWorld(self):
        if not hasattr(self, 'world'):
            rnd = random.Random()
            rnd.seed(self.seed)
            self.world = [
                [rnd.choice(TERRAIN_TYPES) for n in range(64)]
                for m in range(64)]
        return self.world

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
    posX = integer()
    posY = integer()


class RadicalGame(rend.Fragment):
    live = True
    fragmentName = 'radical-game'
    docFactory = loaders.stan(T.div[
        T.span(id='map')['map']])

    def getWorld(self):
        for world in self.original.store.parent.query(RadicalWorld):
            return world.getWorld()
        raise RuntimeError("No world found")

    def goingLive(self, ctx, client):
        world = self.getWorld()
        fName = '/static/radical/%s.png'
        style = 'position: absolute; top: %dpx; left: %dpx'
        self.client = client
        map = flat.flatten(T.div[[
            T.img(src=fName % (world[x][y],), style=style % (y * 64, x * 64))
            for x in range(8) for y in range(8)]])
        print map
        self.client.send(livepage.set('map', map))


registerAdapter(RadicalGame, RadicalCharacter, INavigableFragment)

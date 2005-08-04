
from zope.interface import implements

from twisted.plugin import IPlugin
from twisted.python.components import registerAdapter
from twisted.python import util

from nevow import rend, loaders, livepage, flat, static, tags as T

from axiom import store
from axiom.item import Item
from axiom.attributes import reference, integer

from xmantissa.ixmantissa import INavigableFragment, INavigableElement, ISiteRootPlugin
from xmantissa import webnav, website

class RadicalApplication(Item, website.PrefixURLMixin):
    implements(INavigableElement, ISiteRootPlugin)

    schemaVersion = 1
    typeName = 'radical_application'

    character = reference()

    prefixURL = 'private/radical'

    def install(self):
        self.store.powerUp(self, INavigableElement)
        self.store.powerUp(self, ISiteRootPlugin)
        self.character = RadicalCharacter(store=self.store)

    def getTabs(self):
        return [webnav.Tab('Games', self.storeID, 0.0,
                           [webnav.Tab('Radical',
                                       self.character.storeID,
                                       0.0)],
                           authoritative=False)]

    def createResource(self):
        return static.File(util.sibpath(__file__, 'static'))


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

    def goingLive(self, ctx, client):
        self.client = client
        self.client.send(livepage.set(
            'map',
            flat.flatten(T.div[T.img(src='/private/radical/mountain.png')])))

registerAdapter(RadicalGame, RadicalCharacter, INavigableFragment)

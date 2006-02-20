
from zope.interface import implements

from twisted.python import filepath

from nevow import rend, static

from axiom import item, attributes, queryutil

from xmantissa import ixmantissa


class Game(item.Item, item.InstallableMixin):
    """
    Application powerup which contains all of the non-player game
    state.
    """
    implements(ixmantissa.IPublicPage)

    schemaVersion = 2

    world = attributes.reference(doc="""
    Reference to this game's L{World} instance.
    """)


    def __init__(self, **kw):
        super(Game, self).__init__(**kw)
        if self.world is None:
            self.world = World(store=self.store)


    def installOn(self, other):
        super(Game, self).installOn(other)
        other.powerUp(self, ixmantissa.IPublicPage)


    def getResource(self):
        return RadicalGameResource(self)



class RadicalGameResource(rend.Page):
    def customizeFor(self, username):
        return self


    def childFactory(self, ctx, name):
        if name == 'static':
            return static.File(filepath.FilePath(__file__).parent().child('static').path)
        return None


    def renderHTTP(self, ctx):
        return 'Nothing to see here, yet.'



BARREN = u'barren'

class Terrain(item.Item):
    """
    A small section of the world.
    """
    west = attributes.integer(doc="""
    The west-east coordinate of the northwest corner of this terrain in the
    world.  Bigger is easter.
    """)

    north = attributes.integer(doc="""
    The north-south coordinate of the northwest corner of this terrain
    in the world.  Bigger is souther.
    """)

    east = attributes.integer(doc="""
    The west-east coordinate of the northeast corner of this terrain
    in the world.  Bigger is easter.
    """)

    south = attributes.integer(doc="""
    The north-south coordinate of the southeast corner of this terrain
    in the world.  Bigger is souther.
    """)

    kind = attributes.text(doc="""
    A string/symbolic constant describing this terrain.
    """)

    world = attributes.reference(doc="""
    A reference to the world to which this terrain belongs.
    """)



class World(item.Item):
    """
    Terrain container.

    A world is a giant rectangle.  Behavior of walking off an edge is
    undefined, but probably involves perma-death.

    A world has a bunch of terrain instances associated with it.
    """

    schemaVersion = 2

    width = attributes.integer(doc="""
    The east-west length in FUNDAMENTAL UNITs of the entire world.
    """)

    height = attributes.integer(doc="""
    The north-south length in FUNDAMENTAL UNITs of the entire world.
    """)

    baseGranularity = attributes.integer(doc="""
    The length in FUNDAMENTAL UNITs of the default terrain which is
    created in the world.  This applies to both dimensions.
    """, default=10)

    baseTerrainKind = attributes.text(doc="""
    A string/symbolic constant naming the default kind of terrain
    which is created in the world.
    """, default=BARREN)

    observers = attributes.inmemory()

    def activate(self):
        self.observers = {}
        # As an optimization, we might load all terrain here.


    def movementEvent(self, mover, location):
        for obs in self.observers.get('movement', ()):
            obs(mover, location)


    def observeMovement(self, observer):
        self.observers.setdefault('movement', []).append(observer)
        return lambda: self.observers['movement'].remove(observer)


    def demolish(self):
        """
        Destroy all terrain associated with this world.
        """
        self.store.query(Terrain, Terrain.world == self).deleteFromStore()


    def _quantize(self, coord, upper):
        c = (coord - coord % self.baseGranularity)
        if upper:
            c = c + self.baseGranularity
        return c


    def getTerrain(self, x, y):
        for t in self.store.query(Terrain,
                                  attributes.AND(Terrain.world == self,
                                                 queryutil.contains(Terrain.west,
                                                                    Terrain.east,
                                                                    x),
                                                 queryutil.contains(Terrain.north,
                                                                    Terrain.south,
                                                                    y))):
            return t
        return Terrain(store=self.store,
                world=self,
                west=self._quantize(x, False),
                east=self._quantize(x, True),
                north=self._quantize(y, False),
                south=self._quantize(y, True),
                kind=self.baseTerrainKind)



class RadicalCharacter(item.Item):
    """
    Represents a character in a radical game.

    A single user may have multiple characters.
    """

    schemaVersion = 2

    name = attributes.text(doc="""
    Character's name.
    """)


    _x = attributes.integer(doc="""
    West-east coordinate of this character in the world.
    """, default=0)

    _y = attributes.integer(doc="""
    North-south coordinate of this character in the world.
    """, default=0)

    # Actual (x, y) of this character
    _transientLocation = attributes.inmemory()

    # The World being interacted with.
    world = attributes.inmemory()

    def activate(self):
        self._transientLocation = (self._x, self._y)

    def setWorld(self, world):
        self.world = world

    def getLocation(self):
        return self._transientLocation

    def move(self, (x, y)):
        _x, _y = self._transientLocation
        self._transientLocation = _x + x, _y + y
        self.world.movementEvent(self, self._transientLocation)
        return self._transientLocation

from axiom import upgrade
from twisted.python import reflect

upgrade.registerUpgrader(
    lambda char: char.upgradeVersion(item.normalize(reflect.qual(RadicalCharacter)),
                                     1, 2,
                                     name=char.name, _x=0, _y=0),
    item.normalize(reflect.qual(RadicalCharacter)),
    1, 2)


upgrade.registerUpgrader(
    lambda world: world.upgradeVersion(item.normalize(reflect.qual(World)),
                                       1, 2,
                                       width=world.width,
                                       height=world.height,
                                       baseGranularity=10,
                                       baseTerrainKind=BARREN),
    item.normalize(reflect.qual(World)),
    1, 2)

def _game(game):
    g = game.upgradeVersion(item.normalize(reflect.qual(Game)),
                            1, 2,
                            world=game.world)
    g.installOn(g.store)
    return g

upgrade.registerUpgrader(
    _game,
    item.normalize(reflect.qual(Game)),
    1, 2)

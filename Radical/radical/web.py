
from zope.interface import implements

from twisted.python import components

from nevow import inevow, athena, tags, url, rend, loaders
from nevow.athena import expose

from epsilon import structlike

from axiom import item, attributes, userbase

from xmantissa import ixmantissa, website, webapp, webnav, webtheme, liveform

from radical import model

_static = url.root.child('Radical').child('static')

def imageLocation(name):
    return _static.child('images').child(name + '.png')

def cssLocation(name):
    return _static.child('css').child(name + '.css')


class RadicalUserApplication(item.Item):
    """
    User Powerup which lets someone enter a Radical game.
    """
    implements(ixmantissa.INavigableElement)

    installedOn = attributes.reference(doc="""
    A reference to the avatar on which this application has been installed.
    """)

    powerupInterfaces = (ixmantissa.INavigableElement)


    def getWorld(self):
        # XLaaaaaaworjoaiwuhiu ehakjsehwgyhnesghdakhallllllllalaalallkajkjhkjhakjwproia;lksd;alkd;kjadhsjkhddjshsjshjsjhdshdshdshjd!!
        return self.store.parent.findUnique(userbase.LoginSystem).accountByAddress(u'Radical', None).avatars.open().findUnique(model.World)


    def createCharacter(self, name):
        """
        Create a new Radical character.
        """
        return model.RadicalCharacter(store=self.store,
                                        name=name)


    def getCharacters(self):
        return self.store.query(model.RadicalCharacter)


    def getTabs(self):
        return [webnav.Tab('Games', self.storeID, 0.6,
                           [webnav.Tab('Radical', self.storeID, 1.0)],
                           authoritative=False)]



class CharacterCreationForm(liveform.LiveForm):
    """
    Fragment for initial character configuration.

    This presents the user with a form which allows them to customize
    a character.
    """
    fragmentName = None
    jsClass = u'Radical.World.CharacterCreation'

    def __init__(self, userApp):
        super(CharacterCreationForm, self).__init__(
            self.createCharacter,
            [liveform.Parameter('name',
                                liveform.TEXT_INPUT,
                                unicode,
                                u'The in-game name for this character.')])
        self.userApp = userApp


    def head(self):
        pass


    def createCharacter(self, **kw):
        ch = self.userApp.createCharacter(**kw)
        wtrans = ixmantissa.IWebTranslator(self.userApp.store)
        return {u'name': ch.name,
                u'href': unicode(wtrans.linkTo(ch.storeID), 'ascii')}


class ApplicationFragment(athena.LiveFragment):
    """
    Fragment for overall Radical account information.

    This presents a form for character creation, as well as a list of
    existing characters which may be playable.
    """
    fragmentName = 'radical-application'
    jsClass = u'Radical.World.Application'


    def head(self):
        pass


    def getInitialArguments(self):
        charInfo = []
        wtrans = ixmantissa.IWebTranslator(self.original.store)
        for ch in self.original.getCharacters():
            charInfo.append({u'name': ch.name,
                             u'href': unicode(wtrans.linkTo(ch.storeID), 'ascii')})
        return [charInfo]


    def render_chargenForm(self, ctx, data):
        f = CharacterCreationForm(self.original)
        f.setFragmentParent(self)
        return ctx.tag[f]


components.registerAdapter(ApplicationFragment, RadicalUserApplication, ixmantissa.INavigableFragment)


class RadicalBenefactor(item.Item):
    """
    Dirt stupid benefactor which will install RadicalUserApplication
    and its dependencies on an avatar.
    """

    endowed = attributes.integer(doc="""
    Axiom requires an attribute.  I really don't care about this.  I'm
    not even going to bother with the code to update it.
    """)

    def endow(self, ticket, avatar):
        for app in (website.WebSite, webapp.PrivateApplication, RadicalUserApplication):
            avatar.findOrCreate(app).installOn(avatar)



class CharacterFragment(athena.LiveFragment):
    jsClass = u'Radical.World.Character'

    docFactory = loaders.stan(
        tags.span(_class='radical-character',
                  render=tags.directive('liveFragment')))



class TerrainFragment(rend.Fragment):
    docFactory = loaders.stan(
        tags.img(render=tags.directive('terrainImage')))

    def render_terrainImage(self, ctx, data):
        return ctx.tag(src=imageLocation(self.original.kind))



class SceneFragment(structlike.record('world character'), athena.LiveFragment):
    """
    Renders the underlying terrain visible at the wrapped character's
    location.
    """
    fragmentName = 'radical-terrain'
    jsClass = u'Radical.World.Scene'

    size = model.VISION

    def setFragmentParent(self, parent):
        super(SceneFragment, self).setFragmentParent(parent)
        def onDisconnect(ign, f=self.world.addActiveCharacter(self)):
            f()
        self.page.notifyOnDisconnect().addBoth(onDisconnect)


    def getInitialArguments(self):
        terrain, players = self.character.getVisibleSurroundings()
        return [
            self.character.getLocation(),
            [{u'x': t.x,
              u'y': t.y,
              u'kind': t.kind} for t in terrain],
            [{u'x': p.character.getLocation()[0],
              u'y': p.character.getLocation()[1],
              u'name': p.character.name} for p in players if p is not self],
            self.size]


    # Observers!
    def movementObserver(self, mover, x, y):
        if mover is not self.character:
            loc = self.getLocation()
            if (x is None or y is None) or (abs(loc[0] - x) < 10 and abs(loc[1] - y) < 10):
                self.callRemote('movementObserver', mover.name, x, y)


    def terrainObserver(self, terrain):
        self.callRemote('terrainObserver', {u'x': terrain.x,
                                            u'y': terrain.y,
                                            u'kind': terrain.kind})



    def speechObserver(self, speaker, message):
        self.callRemote('speechObserver', speaker.name, message)


    # Remote methods
    def getTerrain(self):
        loc = self.character.getLocation()
        results = []
        for t in self.world.getTerrainWithin(
            loc[0] - (self.size / 2 + 1),
            loc[1] - (self.size / 2 + 1),
            (self.size + 2),
            (self.size + 2)):
            results.append({
                u'x': t.x,
                u'y': t.y,
                u'kind': t.kind,
                u'passable': True})
        return results
    expose(getTerrain)


    def getLocation(self):
        return self.character.getLocation()
    expose(getLocation)


    def move(self, direction):
        """
        Try to move in the indicated direction.

        Returns a tuple of:

            The new location, as a two-tuple.

            All visible terrain, as a list of dicts with keys u'x', u'y' and u'name'.

            All visible characters, as a list of dicts with keys u'x', u'y' and u'name'.
        """
        if self.character.getLocation()[1] % 2:
            # Normally I detest vertically aligning code like this, but in this
            # particular case it actually seems useful.  I think it's because
            # this actually wants to be a 3 dimensional matrix literal.
            unit = {
                u'west':       (-1,  0),
                u'east':       ( 1,  0),

                u'north':      ( 0, -1),
                u'south':      ( 0,  1),

                u'northwest':  ( 0, -1),
                u'northeast':  ( 1, -1),

                u'southwest':  ( 0,  1),
                u'southeast':  ( 1,  1),
                }[direction]
        else:
            unit = {
                u'west':       (-1,  0),
                u'east':       ( 1,  0),

                u'north':      ( 0, -1),
                u'south':      ( 0,  1),

                u'northwest':  (-1, -1),
                u'northeast':  ( 0, -1),

                u'southwest':  (-1,  1),
                u'southeast':  ( 0,  1),
                }[direction]

        newLocation = self.character.move(unit)
        terrain, players = self.character.getVisibleSurroundings()
        return ({u'x': newLocation[0],
                 u'y': newLocation[1]},
                [{u'x': t.x,
                  u'y': t.y,
                  u'kind': t.kind} for t in terrain],
                [{u'x': p.character.getLocation()[0],
                  u'y': p.character.getLocation()[1],
                  u'name': p.character.name} for p in players if p is not self])
    expose(move)


    def say(self, message):
        self.character.say(message)
    expose(say)



class GameplayFragment(athena.LiveFragment):
    """
    Provides the primary gaming interface, as realized by the
    L{radical.RadicalCharacter} being adapted.
    """
    implements(ixmantissa.INavigableFragment)

    fragmentName = 'radical-gameplay'
    jsClass = u'Radical.World.Gameplay'

    def __init__(self, character):
        super(GameplayFragment, self).__init__()
        self.character = character
        self.world = self.character.store.findUnique(RadicalUserApplication).getWorld()
        self.character.setWorld(self.world)


    def head(self):
        return tags.link(rel='stylesheet', href=cssLocation('radical'))


    def render_scene(self, ctx, data):
        f = SceneFragment(self.world, self.character)
        f.docFactory = webtheme.getLoader(f.fragmentName) # XXX
        f.setFragmentParent(self)
        ctx.tag[f]

#         e = TerrainEditor(self.world, self.character)
#         e.docFactory = webtheme.getLoader(e.fragmentName) # XXX
#         e.setFragmentParent(self)
#         ctx.tag[e]

        return ctx.tag


class GameplayPage(athena.LivePage):
    useActiveChannels = False

    docFactory = loaders.stan(tags.html[tags.head(render=tags.directive('liveglue')),
                                        tags.body(style="overflow: hidden",
                                                  render=tags.directive('everything'))])

    def __init__(self, character):
        self.character = character
        super(GameplayPage, self).__init__(
            jsModuleRoot=url.root.child('private').child('jsmodule'),
            transportRoot=url.root.child('live'))


    def render_everything(self, ctx, data):
        gf = GameplayFragment(self.character)
        gf.docFactory = webtheme.getLoader(gf.fragmentName) # Guess what?  XXX!
        gf.setFragmentParent(self)
        return ctx.tag[gf]

components.registerAdapter(GameplayPage, model.RadicalCharacter, inevow.IResource)

class TerrainEditor(athena.LiveFragment):
    """
    Minimal interface for changing kinds of terrain.
    """
    jsClass = u'Radical.Terrain.Editor'
    fragmentName = 'terrain-editor'

    def __init__(self, world, character):
        super(TerrainEditor, self).__init__(self)
        self.world = world
        self.character = character

    def setTerrainType(self, kind):
        assert kind in (model.BARREN, model.MOUNTAIN, model.GRASS, model.WATER, model.FOREST)
        x, y = self.character.getLocation()
        t = self.world.getTerrain(x, y)
        t.kind = kind
        self.world.terrainEvent(t)
        return x, y
    expose(setTerrainType)


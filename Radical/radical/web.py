
from zope.interface import implements

from twisted.python import components

from nevow import athena, tags, url, json, rend, loaders

from epsilon import structlike

from axiom import item, attributes, userbase

from xmantissa import ixmantissa, website, webapp, webnav, webtheme, liveform

from radical import model

_static = url.root.child('Radical').child('static')

def imageLocation(name):
    return _static.child('images').child(name + '.png')

def cssLocation(name):
    return _static.child('css').child(name + '.css')


class RadicalUserApplication(item.Item, item.InstallableMixin):
    """
    User Powerup which lets someone enter a Radical game.
    """
    implements(ixmantissa.INavigableElement)

    installedOn = attributes.reference(doc="""
    A reference to the avatar on which this application has been
    installed.
    """)

    def installOn(self, other):
        super(RadicalUserApplication, self).installOn(other)
        other.powerUp(self, ixmantissa.INavigableElement)


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


    def render_chargenForm(self, ctx, data):
        f = CharacterCreationForm(self.original)
        f.setFragmentParent(self)
        return ctx.tag[f]


    def render_initArgs(self, ctx, data):
        charInfo = []
        wtrans = ixmantissa.IWebTranslator(self.original.store)
        for ch in self.original.getCharacters():
            charInfo.append({u'name': ch.name,
                             u'href': unicode(wtrans.linkTo(ch.storeID), 'ascii')})
        return ctx.tag[
            tags.textarea(id='init-args-' + str(self._athenaID),
                          style='display: none;')[
                json.serialize(charInfo)]]

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
                  render=tags.directive('liveFragment'))[
            tags.img(render=tags.directive('characterImage'))])


    def render_characterImage(self, ctx, data):
        return ctx.tag(src=imageLocation('player'))


    allowedMethods = {'getLocation': True,
                      'move': True}
    def getLocation(self):
        return self.original.getLocation()


    def move(self, direction):
        return self.original.move({
            u'west': (-1, 0),
            u'east': (1, 0),
            u'north': (0, -1),
            u'south': (0, 1)}[direction])



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

    def render_terrain(self, ctx, data):
        x, y = self.character.getLocation()
        t = self.world.getTerrain(x, y)
        return ctx.tag[TerrainFragment(t)]


    def render_character(self, ctx, data):
        self.charfrag = CharacterFragment(self.character)
        self.charfrag.setFragmentParent(self)
        self.world.observeMovement(self.movementObserver)
        return ctx.tag[self.charfrag]


    # Observers!
    def movementObserver(self, mover, location):
        if mover is not self.character:
            print mover, self.character
            self.callRemote('movementObserver', mover.name, location)




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


    def render_map(self, ctx, data):
        f = SceneFragment(self.world, self.character)
        f.docFactory = webtheme.getLoader(f.fragmentName) # XXX
        f.setFragmentParent(self)
        return ctx.tag[f]

components.registerAdapter(GameplayFragment, model.RadicalCharacter, ixmantissa.INavigableFragment)

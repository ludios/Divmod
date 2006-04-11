
from zope.interface import Interface, Attribute


class ITelnetService(Interface):
    """
    Really lame tag interface used by the Mantissa offering system to uniquely
    identify a powerup that runs a telnet server.
    """


class IDescribeable(Interface):
    """
    A thing which can be described to those with the power of observation.
    """
    def formatTo(whom):
        """
        Return a brief description of this object, as observed by the
        given observer.
        """


    def longFormatTo(whom):
        """
        Return a longer description of this object, as observed by the
        given observer.
        """



class IObjectType(Interface):
    """
    Plugin interface for kinds of objects which can be created in the realm.
    """
    type = Attribute("Name of this type of object.")

    def getType():
        """
        Return a two-argument callable which will be invoked with C{name},
        C{description} to create a new instance of this type.  Should return an
        L{IObject} provider.
        """


class ILinkContributor(Interface):
    """
    A powerup interface which can add more connections between objects in the
    world graph.

    All ILinkContributors which are powered up on a particular Object will be
    given a chance to add to the L{IObject.link} method's return value.
    """

    def links():
        """
        Return a C{dict} mapping names of connections to C{IObjects}.
        """


class IDescriptionContributor(Interface):
    """
    A powerup interface which can add text to the description of an object.

    All IDescriptionContributors which are powered up on a particular Object
    will be given a chance to add to the output of its C{longFormatTo} method.
    """

    def longFormatTo(other):
        """
        @see IDescribeable
        """



class IObject(IDescribeable):
    """
    A thing in the world.  In addition to the behavior described by
    L{IDescribeable}, this has a location and and might be relocateable.
    """
    location = Attribute("An IObject which contains this IObject")

    def canSee(observer):
        """
        Return a boolean indicating whether the given observer can see
        this object.
        """


    def moveTo(where):
        """
        Change this things location to the new location, if possible.
        """



class IActor(Interface):
    hitpoints = Attribute("L{Points} instance representing hit points")
    experience = Attribute("C{int} representing experience")
    level = Attribute("C{int} representing player's level")

    def send(event):
        """Describe something to the actor.

        @type event: L{IDescribeable} provider
        @param event: Something that will be described to the actor.
        """


class IEventObserver(Interface):
    def send(event):
        """Describe something to the actor.

        @type event: L{IDescribeable} provider
        @param event: Something that will be described to the actor.
        """



class IContainer(Interface):
    """
    An object which can contain other objects.
    """
    capacity = Attribute("""
    The maximum weight this container is capable of holding.
    """)

#     lid = Attribute("""
#     A reference to an L{IObject} which serves as this containers lid, or
#     C{None} if there is no lid.
#     """)

    closed = Attribute("""
    A boolean indicating whether this container is closed.
    """)

    def add(object):
        """
        Place the given object into this container.

        @type object: L{IObject}
        @param object: The world object to be added to this container.  Its
        C{location} attribute will be updated if it is successfully added.

        @raise DoesntFit: If there is no room for C{object} in this container.
        @raise Closed: If this container is not currently open.
        """


    def remove(object):
        """
        Remove the given object from this container.

        @type object: L{IObject}

        @param object: The world object which is currently in this container
        which is to be removed.  If it is successfully removed, its C{location}
        attribute will be set to C{None}.

        @raise ValueError: If C{object} is not within this container.
        @raise Closed: If this container is not currently open.
        """


    def contains(other):
        """
        @returns: True if other is in me. And by 'in', I mean 'IN'!  (And
        by 'IN' he means to any arbitrarily deeply nested distance)
        """

    def getContents():
        """
        @returns: An iterable of the direct contents of this container.
        """


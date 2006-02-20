
// import Nevow.Athena

// import Mantissa
// import Mantissa.LiveForm

// import Radical
// import Radical.Geometry

Radical.World = {};

Radical.World.Application = Nevow.Athena.Widget.subclass('Radical.World.Application');
Radical.World.Application.methods(
    function __init__(self, node) {
        Radical.World.Application.upcall(self, '__init__', node);
        var e = document.getElementById('init-args-' + self.objectID);
        self.characterNames = eval(e.value);
        self.addCharacterLinks(self.characterNames);
    },

    function addCharacterLinks(self, charInfo) {
        for (var i = 0; i < charInfo.length; ++i) {
            var d = document.createElement('div');
            var a = document.createElement('a');
            a.appendChild(document.createTextNode(charInfo[i].name));
            a.setAttribute('href', charInfo[i].href);
            d.appendChild(a);
            self.node.appendChild(d);
        }
    });

Radical.World.CharacterCreation = Mantissa.LiveForm.FormWidget.subclass('Radical.World.CharacterCreation');
Radical.World.CharacterCreation.methods(
    function submitSuccess(self, result) {
        self.node.reset();
        self.widgetParent.addCharacterLinks([result]);
    });


/* Class the instances of which represent things which are in some way
   interesting.  These generally correspond to a character or an item visible
   on the map. */
Radical.World.Entity = Divmod.Class.subclass('Radical.World.Entity');
Radical.World.Entity.methods(
    function __init__(self, /* optional */ imageLocation) {
        self.node = document.createElement('span');
        self.node.style.position = 'absolute';

        if (imageLocation != undefined) {
            self.setImage(imageLocation);
        }

        document.body.appendChild(self.node);
    },

    function setImage(self, imageLocation) {
        var img = document.createElement('img');
        img.setAttribute('src', imageLocation);
        self.node.appendChild(img);
    },

    function setPositionByLocation(self, x, y) {
        var pos = Radical.Geometry.absolutePositionFromCoordinates(x, y);
        self.node.style.left = pos.left + 'px';
        self.node.style.top = pos.top + 'px';
    });

Radical.World.Scene = Nevow.Athena.Widget.subclass('Radical.World.Scene');
Radical.World.Scene.methods(
    function __init__(self, node) {
        Radical.World.Scene.upcall(self, '__init__', node);

        /* A mapping of all the things we've seen move around us.  Keys are unique
           identifiers received from the server.  Values are objects containing
           local state about the entitity. */
        self.observedEntities = {};
    },

    function movementObserver(self, moverId, loc) {
        var moverEntity = self.observedEntities[moverId];
        if (moverEntity == undefined) {
            moverEntity = self.initializeEntity(moverId);
        }
        moverEntity.setPositionByLocation(loc[0], loc[1]);
    },

    function initializeEntity(self, entityId) {
        var e = new Radical.World.Entity('/Radical/static/images/player.png');
        self.observedEntities[entityId] = e;
        return e;
    });

Radical.World.Gameplay = Nevow.Athena.Widget.subclass('Radical.World.Gameplay');
Radical.World.Gameplay.methods(
    function __init__(self, node) {
        Radical.World.Gameplay.upcall(self, '__init__', node);
        document.addEventListener('keyup',
                                  function(event) { return self.onKeyPress(event); },
                                  true);
    },

    function onKeyPress(self, event) {
        if (!self.character) {
            // XXX Improve this
            self.character = self.childWidgets[0].childWidgets[0];
        }

        if (!Radical.World.Gameplay.arrowKeys) {
            var m = {};
            m[event.DOM_VK_LEFT] = 'west';
            m[event.DOM_VK_RIGHT] = 'east';
            m[event.DOM_VK_UP] = 'north';
            m[event.DOM_VK_DOWN] = 'south';
            Radical.World.Gameplay.arrowKeys = m;
        }
        var direction = Radical.World.Gameplay.arrowKeys[event.keyCode];
        if (direction) {
            self.character.move(direction);
            event.stopPropagation();
        }
    });

Radical.World.Character = Nevow.Athena.Widget.subclass('Radical.World.Character');
Radical.World.Character.methods(
    function __init__(self, node) {
        Radical.World.Character.upcall(self, '__init__', node);
        self.callRemote('getLocation').addCallback(
            function(loc) {
                self.setPositionByLocation(loc[0], loc[1])
                self.node.style.display = 'inline';
            });
    },

    function setPositionByLocation(self, x, y) {
        var pos = Radical.Geometry.absolutePositionFromCoordinates(x, y);
        self.node.style.left = pos.left + 'px';
        self.node.style.top = pos.top + 'px';
    },

    function move(self, direction) {
        var d = self.callRemote('move', direction);
        d.addCallback(function(loc) {
            self.setPositionByLocation(loc[0], loc[1]);
        });
    });

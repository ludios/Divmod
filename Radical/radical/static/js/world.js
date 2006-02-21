
// import Nevow.Athena

// import Mantissa
// import Mantissa.LiveForm

// import Radical
// import Radical.Artwork
// import Radical.Geometry

Radical.World = {};

Radical.World.getTerrainURL = function(x, y) {
    return Radical.Artwork.terrainLocation(Radical.World.getTerrain(x, y));
};

Radical.World.getTerrain = function(x, y) {
    return Radical.World._terrainTypes[(x + y) % Radical.World._terrainTypes.length];
};


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
    function __init__(self, scene, /* optional */ imageLocation) {
        self.scene = scene;
        self.node = document.createElement('span');
        self.node.style.position = 'absolute';

        if (imageLocation != undefined) {
            self.setImage(imageLocation);
        }

        document.body.appendChild(self.node);
    },

    function setCoordinates(self, x, y) {
        self.x = x;
        self.y = y;
        if (self.img) {
            self.scene.viewport.setItemImagePosition(self.img, x, y);
        }
    },

    function setImage(self, imageLocation) {
        if (self.img != undefined) {
            self.node.removeChild(self.img);
        }
        self.img = document.createElement('img');
        self.img.src = imageLocation;
        self.img.style.position = 'absolute';
        if (self.x != undefined) {
            self.scene.viewport.setItemImagePosition(self.img, self.x, self.y);
        }
        self.node.appendChild(self.img);
    });

Radical.World._terrainTypes = ['barren', 'water', 'grass', 'forest', 'mountain'];

Radical.World.Scene = Nevow.Athena.Widget.subclass('Radical.World.Scene');
Radical.World.Scene.methods(
    function __init__(self, node) {
        Radical.World.Scene.upcall(self, '__init__', node);

        self.viewport = new Radical.Geometry.Viewport(0, 0, 16, 16);

        /* A mapping of all the things we've seen move around us.  Keys are
           unique identifiers received from the server.  Values are objects
           containing local state about the entitity. */
        self.observedEntities = {
            'player': new Radical.World.Character(self)
        };

        self._viewportResized();
    },

    function _viewportResized(self) {
        /*
         * An Array of img tags representing the currently visible terrain.
         */
        self.terrain = new Array(self.viewport.width * self.viewport.height);

        /*
         * Some more information about that visible terrain.
         */
        self.terrainInfo = new Array(self.viewport.width * self.viewport.height);

        /*
         * Initial the field to something random.  Lala.
         */
        for (var y = 0; y < self.viewport.height; ++y) {
            for (var x = 0; x < self.viewport.width; ++x) {
                self.setTerrain(x, y, Radical.World.getTerrain(x, y), true);
            }
        }

        /*
         * Load the actually visible terrain.
         */
        self.callRemote('getTerrain').addCallback(function(result) {
            for (var i = 0; i < result.length; ++i) {
                var x = result[i].x,
                    y = result[i].y,
                    kind = result[i].kind,
                    passable = result[i].passable;

                    self.setTerrain(x, y, kind, passable);
            }
        });
    },

    function getTerrainInfo(self, col, row) {
        var ti;
        if (col >= 0 && col < self.viewport.width && row >= 0 && row < self.viewport.height) {
            ti = self.terrainInfo[row * self.viewport.width + col];
        }
        if (ti == undefined) {
            Divmod.msg("No terrain info for " + col + ", " + row + ".");
            return {'kind': 'barren', 'passable': false};
        }
        return ti;
    },

    function setTerrain(self, col, row, kind, passable) {
        var idx = row * self.viewport.width + col;
        var img = self.terrain[idx]
        if (img == undefined) {
            img = self.terrain[idx] = document.createElement('img');
            img.style.position = 'absolute';
            self.viewport.setTerrainImagePosition(img, col, row);
            self.node.appendChild(img);
            self.terrainInfo[idx] = {};
        }
        img.src = Radical.Artwork.terrainLocation(kind);
        self.terrainInfo[idx].kind = kind;
        self.terrainInfo[idx].passable = passable;
    },

    function movementObserver(self, moverId, loc) {
        var moverEntity = self.observedEntities[moverId];
        if (moverEntity == undefined) {
            moverEntity = self.initializeEntity(moverId);
        }
        moverEntity.x = loc[0];
        moverEntity.y = loc[1];
        if (moverEntity.img) {
            Radical.Geometry.setItemImagePosition(moverEntity.img, loc[0], loc[1]);
        }
    },

    function initializeEntity(self, entityId) {
        var e = new Radical.World.Entity(self, Radical.Artwork.playerLocation('small-red'));
        self.observedEntities[entityId] = e;
        return e;
    },

    function scrollNorth(self) {
        self.viewport.top -= 2;

        for (var y = self.viewport.height - 3; y >= 0; --y) {
            for (var x = 0; x < self.viewport.width; ++x) {
                var idx = y * self.viewport.width + x;
                var t = self.terrain[idx];
                var ti = self.terrainInfo[idx];

                self.terrain[idx + (self.viewport.width * 2)].src = t.src;
                self.terrainInfo[idx + (self.viewport.width * 2)] = ti;
            }
        }

        for (var y = 0; y < 2; ++y) {
            for (var x = 0; x < self.viewport.width; ++x) {
                var idx = y * self.viewport.width + x;
                self.terrain[idx].src = Radical.Artwork.terrainLocation('water');
                Divmod.msg("Assigned new terrain type to " + idx);
            }
        }
        for (var entId in self.observedEntities) {
            var e = self.observedEntities[entId];
            if (e.img) {
                self.viewport.setItemImagePosition(e.img, e.x, e.y);
            }
        }

    },

    function scrollSouth(self) {
        self.viewport.top += 2;

        for (var y = 2; y < self.viewport.height; ++y) {
            for (var x = 0; x < self.viewport.width; ++x) {
                var idx = y * self.viewport.width + x;
                var t = self.terrain[idx];
                var ti = self.terrainInfo[idx];

                self.terrain[idx - (self.viewport.width * 2)].src = t.src;
                self.terrainInfo[idx - (self.viewport.width * 2)] = ti;
            }
        }

        for (var y = self.viewport.height - 3; y < self.viewport.height; ++y) {
            for (var x = 0; x < self.viewport.width; ++x) {
                var idx = y * self.viewport.width + x;
                self.terrain[idx].src = Radical.Artwork.terrainLocation('grass');
                Divmod.msg("Assigned new terrain type to " + idx);
            }
        }

        for (var entId in self.observedEntities) {
            var e = self.observedEntities[entId];
            if (e.img) {
                self.viewport.setItemImagePosition(e.img, e.x, e.y);
            }
        }
    },

    function scrollWest(self) {
        self.viewport.left -= 2;

        for (var x = self.viewport.width - 3; x >= 0; --x) {
            for (var y = 0; y < self.viewport.height; ++y) {
                var idx = y * self.viewport.width + x;
                var t = self.terrain[idx];
                var ti = self.terrainInfo[idx];

                self.terrain[idx + 2].src = t.src;
                self.terrainInfo[idx + 2] = ti;
            }
        }

        for (var x = 0; x < 2; ++x) {
            for (var y = 0; y < self.viewport.height; ++y) {
                var idx = y * self.viewport.width + x;
                self.terrain[idx].src = Radical.Artwork.terrainLocation('forest');
            }
        }

        for (var entId in self.observedEntities) {
            var e = self.observedEntities[entId];
            if (e.img) {
                self.viewport.setItemImagePosition(e.img, e.x, e.y);
            }
        }
    },

    function scrollEast(self) {
        self.viewport.left += 2;

        for (var x = 2; x < self.viewport.width; ++x) {
            for (var y = 0; y < self.viewport.height; ++y) {
                var idx = y * self.viewport.width + x;
                var t = self.terrain[idx];
                var ti = self.terrainInfo[idx];

                self.terrain[idx - 2].src = t.src;
                self.terrainInfo[idx - 2] = ti;
            }
        }

        for (var x = self.viewport.width - 3; x < self.viewport.width; ++x) {
            for (var y = 0; y < self.viewport.height; ++y) {
                var idx = y * self.viewport.width + x;
                self.terrain[idx].src = Radical.Artwork.terrainLocation('mountain');
            }
        }

        for (var entId in self.observedEntities) {
            var e = self.observedEntities[entId];
            if (e.img) {
                self.viewport.setItemImagePosition(e.img, e.x, e.y);
            }
        }
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
            self.character = self.childWidgets[0].observedEntities['player'];
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
            event.preventDefault();
            event.preventBubble();
            event.cancelBubble = true;
        }
    });

Radical.World._movementOffsets = {
    'west': [-1, 0],
    'east': [1, 0],
    'north': [0, -1],
    'south': [0, 1]
};

Radical.World.Character = Radical.World.Entity.subclass('Radical.World.Character');
Radical.World.Character.methods(
    function __init__(self, scene) {
        Radical.World.Character.upcall(self, '__init__', scene, Radical.Artwork.playerLocation('small-red'));
        self.node.style.zIndex = 1;

        self.scene.callRemote('getLocation').addCallback(
            function(loc) {
                self.setCoordinates(loc[0], loc[1]);
            });
    },

    function move(self, direction) {
        var viewport = self.scene.viewport;
        var off = Radical.World._movementOffsets[direction];
        self.x += off[0];
        self.y += off[1];
        var terrain = self.scene.getTerrainInfo(self.x - viewport.left, self.y - viewport.top);
        if (terrain.passable || true) {
            if (direction == 'west' && (self.x - viewport.left) < 3) {
                self.scene.scrollWest();
            } else if (direction == 'east' && (self.x - viewport.left) > 12) {
                self.scene.scrollEast();
            } else if (direction == 'north' && (self.y - viewport.top) < 3) {
                self.scene.scrollNorth();
            } else if (direction == 'south' && (self.y - viewport.top) > 12) {
                self.scene.scrollSouth();
            } else {
                self.scene.viewport.setItemImagePosition(self.img, self.x, self.y);
            }

            var d = self.scene.callRemote('move', direction);
        }
    });

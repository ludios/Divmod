
// import Nevow.Athena

// import Mantissa
// import Mantissa.LiveForm

// import Radical
// import Radical.Artwork
// import Radical.Geometry

Radical.World = {};

Radical.World.Application = Nevow.Athena.Widget.subclass('Radical.World.Application');
Radical.World.Application.methods(
    function __init__(self, node) {
        Radical.World.Application.upcall(self, '__init__', node);
        var e = document.getElementById('init-args-' + self.objectID);
        self.characterNames = eval('(' + e.value + ')');
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
        self.img = null;
        if (imageLocation != undefined) {
            self.setImage(imageLocation);
        }
    },

    function setImage(self, imageLocation) {
        if (self.img && self.img.parentNode) {
            self.img.parentNode.removeChild(self.img);
        }
        self.img = document.createElement('img');
        self.img.style.position = 'absolute';
        self.img.style.display = 'none';
        self.img.src = imageLocation;
        self.img.onload = function() {
            self.img.onload = null;
            Divmod.msg("Entity loaded, painting viewport");
            self.scene.viewport.paint();
            self.img.style.display = '';
        };
        document.body.appendChild(self.img);
        Divmod.msg("An entity arrived on the page: " + self.img.src);
    });

Radical.World._terrainTypes = ['barren', 'water', 'grass', 'forest', 'mountain'];

Radical.World.Scene = Nevow.Athena.Widget.subclass('Radical.World.Scene');
Radical.World.Scene.methods(
    /*
     * Keeps track of environment, items and characters.  Keeps a limited cache
     * of terrain which is updated when the character moves around.  Is
     * responsible for telling the viewport to redraw and move around and such.
     */
    function __init__(self, node) {
        Radical.World.Scene.upcall(self, '__init__', node);

        self.terrainCache = {};

        var initargs = eval('(' + document.getElementById('scene-args-' + self.objectID).value + ')');
        var center = initargs.center;
        var terrain = initargs.terrain;
        var players = initargs.players;
        var size = initargs.size;

        self.viewport = new Radical.Geometry.Viewport(self, center[0] - size / 2, center[1] - size / 2, size, size);
        self.node.appendChild(self.viewport.evenNode);
        self.node.appendChild(self.viewport.oddNode);

        /* A mapping of all the things we've seen move around us.  Keys are
           unique identifiers received from the server.  Values are objects
           containing local state about the entitity. */
        self.observedEntities = {
            'player': new Radical.World.Character(self, center[0], center[1])
        };

        Divmod.msg("There is terrain: " + terrain.length);

        for (var i = 0; i < terrain.length; ++i) {
            self.cacheTerrainInfo(terrain[i].x, terrain[i].y, terrain[i].kind);
        }

        Divmod.msg("There is players: " + players.length);

        for (var i = 0; i < players.length; ++i) {
            self.movementObserver(players[i].name, players[i].x, players[i].y);
        }

        self.paint();
    },

    function cacheTerrainInfo(self, col, row, info) {
        self.terrainCache[col + 'x' + row] = info;
    },

    function getTerrainKind(self, col, row) {
        var result = self.terrainCache[col + 'x' + row];
        if (result == undefined) {
            return null;
        }
        return result;
    },

    function movementObserver(self, moverId, x, y) {
        var moverEntity = self.observedEntities[moverId];

        if (x == null && y == null) {
            if (moverEntity != undefined) {
                delete self.observedEntities[moverId];
                if (moverEntity.img) {
                    moverEntity.img.parentNode.removeChild(moverEntity.img);
                }
            }
        } else {
            if (moverEntity == undefined) {
                Divmod.msg("Creating a new entity: " + moverId);
                moverEntity = self.initializeEntity(moverId);
            }
            var oldx = moverEntity.x,
                oldy = moverEntity.y;
            moverEntity.x = x;
            moverEntity.y = y;
            self.viewport._paintEntity(moverEntity);
        }
    },

    function terrainObserver(self, terrain) {
        self.cacheTerrainInfo(terrain.x, terrain.y, terrain.kind);
        if (self.viewport.visible(terrain.x, terrain.y)) {
            Divmod.msg("Received terrain update, repainting");
            self.paint();
        } else {
            Divmod.msg("Received irrelevant terrain update");
        }
    },

    function initializeEntity(self, entityId) {
        var e = new Radical.World.Entity(self, Radical.Artwork.playerLocation('medium-red'));
        self.observedEntities[entityId] = e;
        return e;
    },

    function terrainClicked(self, x, y) {
        Divmod.msg("terrainClicked(" + x + ", " + y + ")");
        self.widgetParent.tryWalkTo(x, y);
    },

    function paint(self) {
        self.viewport.paint();
    });

Radical.World.Gameplay = Nevow.Athena.Widget.subclass('Radical.World.Gameplay');
Radical.World.Gameplay.methods(
    function __init__(self, node) {
        Radical.World.Gameplay.upcall(self, '__init__', node);
        document.addEventListener('keyup',
                                  function(event) { return self.onKeyPress(event); },
                                  true);
        document.addEventListener('keypress',
                                  function(event) {
                                      if (Radical.World.Gameplay.arrowKeys && event.keyCode in Radical.World.Gameplay.arrowKeys) {
                                          return self.kill(event);
                                      }
                                  },
                                  true);
        self._walkId = 0;
    },

    function kill(self, event) {
        event.stopPropagation();
        event.preventDefault();
        event.preventBubble();
        event.cancelBubble = true;
        return false;
    },

    function tryWalkTo(self, x, y) {
        if (!self.character) {
            // XXX Improve this
            self.character = self.childWidgets[0].observedEntities['player'];
        }

        self._walkId += 1;

        var northsouth = '';
        var eastwest = '';
        // Super stupid algorithm - just walk straight there.
        if (self.character.x < x) {
            Divmod.msg(self.character.x + " is less than " + x + " so going EEEE.");
            eastwest = 'east';
        } else if (self.character.x > x) {
            Divmod.msg(self.character.x + " is greater than " + x + " so going WWWW.");
            eastwest = 'west';
        }

        if (self.character.y < y) {
            Divmod.msg(self.character.y + " is less than " + y + " so going SSSSS.");
            northsouth = 'south';
        } else if (self.character.y > y) {
            Divmod.msg(self.character.y + " is greater than " + y + " so going NNNNN.");
            northsouth = 'north';
        }

        var d = northsouth + eastwest;

        if (d.length) {
            var moved = self.character.move(d);
            if (moved != null) {
                moved.addCallback(function(ign, walkId) {
                    if (self._walkId == walkId) {
                        self.tryWalkTo(x, y);
                    }
                }, self._walkId);
            }
        }
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
            m[event.DOM_VK_HOME] = 'northwest';
            m[event.DOM_VK_PAGE_UP] = 'northeast';
            m[event.DOM_VK_END] = 'southwest';
            m[event.DOM_VK_PAGE_DOWN] = 'southeast';
            Radical.World.Gameplay.arrowKeys = m;
        }
        var direction = Radical.World.Gameplay.arrowKeys[event.keyCode];
        if (direction) {
            self.character.move(direction);
            return self.kill(event);
        }
    });

Radical.World.Character = Radical.World.Entity.subclass('Radical.World.Character');
Radical.World.Character._oddMovementOffsets = {
    west:       [-1,  0],
    east:       [ 1,  0],

    north:      [ 0, -1],
    south:      [ 0,  1],

    northwest:  [ 0, -1],
    northeast:  [ 1, -1],

    southwest:  [ 0,  1],
    southeast:  [ 1,  1]};

Radical.World.Character._evenMovementOffsets = {
    west:       [-1,  0],
    east:       [ 1,  0],

    north:      [ 0, -1],
    south:      [ 0,  1],

    northwest:  [-1, -1],
    northeast:  [ 0, -1],

    southwest:  [-1,  1],
    southeast:  [ 0,  1]};

Radical.World.Character.methods(
    function __init__(self, scene, x, y) {
        Radical.World.Character.upcall(self, '__init__', scene, Radical.Artwork.playerLocation('medium-red'));
        self.img.style.zIndex = 1;
        self.moving = false;

        self.scrollStyle = 'flip'; // or 'slide'

        self.x = x;
        self.y = y;

        self.worldPos = document.createElement('span');
        document.body.appendChild(self.worldPos);
    },

    function move(self, direction) {
        if (!self.moving) {
            // self.moving = true;
            var before = new Date();

            var change;
            if (self.y % 2) {
                change = Radical.World.Character._oddMovementOffsets[direction];
            } else {
                change = Radical.World.Character._evenMovementOffsets[direction];
            }
            var relx = self.x - self.scene.viewport.x;
            var rely = self.y - self.scene.viewport.y;
            var scroll = false;

            if (self.scrollStyle == 'slide') {
                // This version scrolls by one when you get near the edge of the screen.
                if (relx + change[0] < 3 || relx + change[0] > self.scene.viewport.width - 3) {
                    self.scene.viewport.x += change[0];
                    scroll = true;
                }

                if (rely + change[1] < 3 || rely + change[1] > self.scene.viewport.height - 3) {
                    self.scene.viewport.y += change[1];
                    scroll = true;
                }
            } else if (self.scrollStyle == 'flip') {
                // This version scrolls by the width/height of the screen when you
                // get past the edge of the screen.
                if (relx + change[0] < 0 || relx + change[0] >= self.scene.viewport.width) {
                    self.scene.viewport.x += (self.scene.viewport.width * change[0]);
                    scroll = true;
                }

                if (rely + change[1] < 0 || rely + change[1] >= self.scene.viewport.height) {
                  self.scene.viewport.y += (self.scene.viewport.height * change[1]);
                  scroll = true;
                }
            }

            // Ha ha go cast waterwalk on yourself or something.
            if (self.scene.getTerrainKind(self.x + change[0], self.y + change[1]) == 'water') {
                return;
            }

            self.x += change[0];
            self.y += change[1];
            self.worldPos.innerHTML = self.x + ', ' + self.y;

            var d = self.scene.callRemote('move', direction).addCallback(function(result) {
                var after = new Date();
                Divmod.msg("move roundtrip was " + (after.valueOf() - before.valueOf()));
                before = new Date();

                // self.moving = false;

                var pos = result[0],
                    ter = result[1],
                    chs = result[2];

                Divmod.msg("Adding " + ter.length + " terrains to the cache.");

                for (var i = 0; i < ter.length; ++i) {
                    self.scene.cacheTerrainInfo(ter[i].x, ter[i].y, ter[i].kind);
                }

                Divmod.msg("There are " + chs.length + " characters.");
                for (var i = 0; i < chs.length; ++i) {
                    self.scene.movementObserver(chs[i].name, chs[i].x, chs[i].y);
                }

                after = new Date();
                Divmod.msg("move callback was " + (after.valueOf() - before.valueOf()));
            });

            if (scroll) {
                self.scene.paint();
            } else {
                self.scene.viewport._paintEntity(self);
            }
            return d;
        }
        return null;
    });

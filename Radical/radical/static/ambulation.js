
var VIEWPORT_X = 8;
var VIEWPORT_Y = 8;

var theMap = null;

function mapTileImageSource(kind) {
    /* Return the URL for the image representing the terrain of the
     * given kind.
     */
    return '/static/radical/' + kind + '.png';
};

function GameObject(row, col, node) {
    this.row = row;
    this.col = col;
    this.node = node;
};

function GameMap_erase() {
    this.element.innerHTML = '';
};

function GameMap_redraw() {
    var idx = 0;
    for (row = 0; row < this.terrain.length; row++) {
        for (col = 0; col < this.terrain[row].length; col++) {
            imgSrc = mapTileImageSource(this.terrain[row][col]);
            this.tiles[idx].firstChild.src = imgSrc;
            idx++;
        }
    }
};

function GameMap_insertTopRow(terrain) {
    /* Move everything on the screen down one.  Insert the given
     * terrain in the new, empty row at the top.
     */
    contents = this.contents;
    this.contents = []
    for (n = 0; n < contents.length; n++) {
        contents[n].row += 1;
        if (contents[n] < VIEWPORT_Y) {
            this.contents.push(contents[n]);
        }
    }

    this.terrain.unshift(terrain);
    this.terrain.pop();
    this.redraw();
};

function GameMap_insertBottomRow(terrain) {
    /* Opposite of insertTopRow
     */
    contents = this.contents;
    this.contents = []
    for (n = 0; n < contents.length; n++) {
        contents[n].row -= 1;
        if (contents[n] >= 0) {
            this.contents.push(contents[n]);
        }
    }

    this.terrain.push(terrain);
    this.terrain.shift();
    this.redraw();
};

function GameMap_insertLeftColumn(terrain) {
    /* Move everything to the left and insert the given terrain in the
     * new empty column.
     */
    contents = this.contents;
    this.contents = []
    for (n = 0; n < contents.length; n++) {
        contents[n].col -= 1;
        if (contents[n] >= 0) {
            this.contents.push(contents[n]);
        }
    }

    for (n = 0; n < terrain.length; n++) {
        this.terrain[n].push(terrain[n]);
        this.terrain[n].shift();
    }
    this.redraw();
};


function GameMap_insertRightColumn(terrain) {
    /* Move everything to the left and insert the given terrain in the
     * new empty column.
     */
    contents = this.contents;
    this.contents = []
    for (n = 0; n < contents.length; n++) {
        contents[n].col += 1;
        if (contents[n] < VIEWPORT_Y) {
            this.contents.push(contents[n]);
        }
    }

    for (n = 0; n < terrain.length; n++) {
        this.terrain[n].unshift(terrain[n]);
        this.terrain[n].pop();
    }
    this.redraw();
};



function GameMap(terrain) {
    this.terrain = terrain
    this.width = terrain.length;
    this.height = terrain[0].length;
    this.contents = [];

    this.element = document.getElementById('map-node');

    this.tiles = [];
    for (row = 0; row < this.terrain.length; row++) {
        for (col = 0; col < this.terrain[row].length; col++) {
            tile = createMapTile(row, col, this.terrain[row][col]);
            this.tiles[this.tiles.length] = tile;
            this.element.appendChild(tile);
        }
    }

    this.erase = GameMap_erase;
    this.redraw = GameMap_redraw;
    this.insertTopRow = GameMap_insertTopRow;
    this.insertBottomRow = GameMap_insertBottomRow;
    this.insertLeftColumn = GameMap_insertLeftColumn;
    this.insertRightColumn = GameMap_insertRightColumn;
};

function mapTileNodeId(x, y) {
    /* Return the node ID of the map tile at the given location. */
    return 'tile-' + new String(x) + new String(y);
};

function setTerrain(x, y, kind) {
    /* Update the map by setting the terrain at the given tile
     * location to the given kind.
     */
    var tileId = mapTileNodeId(x, y);
    document.getElementById(tileId).setAttribute('src', mapTileImageSource(kind));
};

function absolutePositionFromCoordinates(row, col) {
    return [75 + row * 64, 175 + col * 64];
};

function createMapTile(row, col, kind) {
    /* Create a completely initialized map tile at the given location
     * and with the given terrain type.
     */
    var image = document.createElement('img');
    image.setAttribute('src', mapTileImageSource(kind));

    var pos = absolutePositionFromCoordinates(row, col);

    var tile = document.createElement('div');
    tile.setAttribute('id', mapTileNodeId(col, row));
    tile.style.position = 'absolute';
    tile.style.top = new String(pos[0]) + 'px';
    tile.style.left = new String(pos[1]) + 'px';
    tile.appendChild(image);

    return tile;
};

function initializeMap(terrain) {
    /* Create a game map by creating a bunch of divs at particular
     * locations.  For now, the divs each contain only an img.
     */
    theMap = new GameMap(terrain);
    theMap.redraw();
};

function characterTileImageSource(image) {
    return '/static/radical/' + image + '.png';
};

function createCharacterTile(charId, charImageURL) {
    var node = document.createElement('span');
    var charImage = document.createElement('img');
    var charMessage = document.createElement('div');

    node.id = charId;
    charImage.src = charImageURL;

    charMessage.style.cssText = 'background-color: white; opacity: 100; visibility: hidden; border-style: solid; border-color: red';

    node.appendChild(charMessage);
    node.appendChild(charImage);

    return node;
};

function moveCharacterTile(charNode, row, col) {
    var pos = absolutePositionFromCoordinates(row, col);
    charNode.style.cssText = 'position: absolute; top: ' + new String(pos[0]) + 'px; left: ' + new String(pos[1]) + 'px; z-index: 2;';
};

function characterId(charId) {
    return 'character-' + charId;
};

function eraseCharacter(charId) {
    var node = document.getElementById(characterId(charId));
    if (node) {
        theMap.element.removeChild(node);
        for (n = 0; n < theMap.contents.length; n++) {
            if (theMap.contents[n].node == node) {
                theMap.contents.splice(n, 1);
                break;
            }
        }
    }
};


function moveCharacter(charId, row, col, charImage) {
    var node = document.getElementById(characterId(charId));
    if (!node) {
        node = createCharacterTile(characterId(charId), characterTileImageSource(charImage));
        theMap.element.appendChild(node);
        theMap.contents[theMap.contents] = node;
    }
    moveCharacterTile(node, row, col);
};

function displayCharacter(row, col, image) {
    var charTile = createCharacterTile(row, col, image);
    theMap.element.appendChild(charTile);
};

function appendMessage(charId, message) {
    var node = document.getElementById(characterId(charId));
    var messageNode = node.firstChild;

    messageNode.innerHTML = message;
    messageNode.style.visibility = 'visible';
    window.setTimeout(function() {
                          if (messageNode.innerHTML == message) {
                              messageNode.style.visibility = 'hidden';
                          };
                      }, 10000);

};


function onKeyPress(event) {
    /* Capture keystrokes and report them to the server.
     */
    if (event.keyCode == event.DOM_VK_LEFT) {
        server.handle('leftArrow');
    } else if (event.keyCode == event.DOM_VK_RIGHT) {
        server.handle('rightArrow');
    } else if (event.keyCode == event.DOM_VK_UP) {
        server.handle('upArrow');
    } else if (event.keyCode == event.DOM_VK_DOWN) {
        server.handle('downArrow');
    } else {
        server.handle('keyPress',
                      String.fromCharCode(event.which),
                      event.altKey, event.ctrlKey, event.metaKey,
                      event.shiftKey);
    }
};

document.onkeypress = onKeyPress;

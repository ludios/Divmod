
// Width and height, in tiles, of the viewport onto the world map
var VIEWPORT_X = 8;
var VIEWPORT_Y = 8;

// Reference to the single instance of GameMap
var theMap = null;

// Pixel position of the top, left corner of the map area
var MAP_TOP_PX = 75;
var MAP_LEFT_PX = 175;

// Pixel size of each tile
var TILE_WIDTH_PX = 128;
var TILE_HEIGHT_PX = 96;

// Pixel size of each object which can occupy a tile
var OBJECT_WIDTH_PX = 128;
var OBJECT_HEIGHT_PX = 128;

// How many messages are in the notification area
var messageCount = 0;

// Text displayed in the notification area when the page loads
var introductoryInstructions = (
    'Welcome to Radical.  Use the arrow keys to move around.  ' +
    'Use \' to focus the chat box.  Have fun!');

// Display some information in the notification area, if debugging is enabled
function debug(message) {
    if (false) {
        notify(message);
    }
}

// Display some information in the notification area.  Bump the oldest
// thing if the area is full.
function notify(message) {
    var notification = document.getElementById('notification');
    var d = document.createElement('div');
    var t = document.createTextNode(message);
    d.appendChild(t);
    notification.appendChild(d);
    messageCount++;
    if (messageCount > 10) {
        notification.removeChild(notification.firstChild);
        messageCount--;
    }
}

// Kind of like Python's vars() builtin
function strvars(obj) {
    var accum = [];
    for (e in obj) {
        accum.push(e + ': ' + obj[e]);
    }
    return '{' + accum.join(', ') + '}';
}

// Position the given node absolutely at the indicated pixel coordinate
function setNodePosition(node, left, top) {
    node.style.position = 'absolute';
    node.style.left = left + 'px';
    node.style.top = top + 'px';
}


function mapTileImageSource(kind) {
    /* Return the URL for the image representing the terrain of the
     * given kind.
     */
    return '/static/radical/' + kind + '.png';
};

// Position of a tile at the given tile-based coordinate
function absolutePositionFromCoordinates(row, col) {
    return [MAP_LEFT_PX + row * TILE_WIDTH_PX, MAP_TOP_PX + col * TILE_HEIGHT_PX];
};

// Position of an object occupying a tile at the given tile-based coordinate
function absoluteObjectPositionFromCoordinates(row, col) {
    var tilePos = absolutePositionFromCoordinates(row, col);

    // The goal here is to center the middle of the bottom of the
    // image in the middle of the tile it occupies.  These coordinates
    // are for the top-left of the image, though.

    tileCenterX = tilePos[0] + TILE_WIDTH_PX / 2;
    tileCenterY = tilePos[1] + TILE_HEIGHT_PX / 2;

    objLeft = tileCenterX - OBJECT_WIDTH_PX / 2;
    objTop = tileCenterY - OBJECT_HEIGHT_PX;

    return [objLeft, objTop];
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

    var pos = null;
    for (var n = 0; n < this.contents.length; n++) {
        obj = this.contents[n];
        pos = absoluteObjectPositionFromCoordinates(obj.row, obj.col);
        setNodePosition(obj, pos[0], pos[1]);
        debug("Rendering " + new String(obj.id) + " at " + pos.join(', '));
    }
};

function GameMap_insertTopRow(terrain, items) {
    /* Move everything on the screen down one.  Insert the given
     * terrain in the new, empty row at the top.
     */
    notify('Insert top row: ' + JSON.stringify(items));

    contents = this.contents;
    this.contents = [this.contents[0]];
    for (n = 1; n < contents.length; n++) {
        contents[n].col += 1;
        debug('Shifting ' + new String(contents[n].id) + ' right.');
        if (contents[n].col < VIEWPORT_Y) {
            this.contents.push(contents[n]);
        } else {
            this.element.removeChild(contents[n]);
            debug('It is off the screen!');
        }
    }

    for (n = 0; n < terrain.length; n++) {
        this.terrain[n].unshift(terrain[n]);
        this.terrain[n].pop();
        if (items[n]) {
            for (m = 0; m < items[n].length; m++) {
                var itemNode = createItemTile(n, 0, m, items[n][m]);
                this.contents.push(itemNode);
                this.element.appendChild(itemNode);
            }
        }
    }
    this.redraw();
};

function GameMap_insertBottomRow(terrain, items) {
    /* Opposite of insertTopRow
     */
    notify('Insert bottom row: ' + JSON.stringify(items));

    contents = this.contents;
    this.contents = [this.contents[0]];
    for (n = 1; n < contents.length; n++) {
        contents[n].col -= 1;
        debug('Shifting ' + new String(contents[n]) + ' left.');
        if (contents[n].col >= 0) {
            this.contents.push(contents[n]);
        } else {
            this.element.removeChild(contents[n]);
            debug('It is off the screen!');
        }
    }

    for (n = 0; n < terrain.length; n++) {
        this.terrain[n].push(terrain[n]);
        this.terrain[n].shift();
        if (items[n]) {
            for (m = 0; m < items[n].length; m++) {
                var itemNode = createItemTile(n, VIEWPORT_Y - 1, m, items[n][m]);
                this.contents.push(itemNode);
                this.element.appendChild(itemNode);
            }
        }
    }
    this.redraw();
};

function GameMap_insertLeftColumn(terrain, items) {
    /* Move everything to the right and insert the given terrain in the
     * new empty column.
     */
    contents = this.contents;
    this.contents = [this.contents[0]];
    for (n = 1; n < contents.length; n++) {
        debug('Shifting ' + new String(contents[n].id) + ' down.');
        contents[n].row += 1;
        if (contents[n].row < VIEWPORT_Y) {
            this.contents.push(contents[n]);
        } else {
            this.element.removeChild(contents[n]);
            debug('It is off the screen!');
        }
    }

    this.terrain.unshift(terrain);
    this.terrain.pop();

    for (n = 0; n < terrain.length; n++) {
        if (items[n]) {
            for (m = 0; m < items[n].length; m++) {
                var itemNode = createItemTile(0, n, m, items[n][m]);
                this.contents.push(itemNode);
                this.element.appendChild(itemNode);
            }
        }
    }

    this.redraw();
};


function GameMap_insertRightColumn(terrain, items) {
    /* Move everything to the left and insert the given terrain in the
     * new empty column.
     */
    contents = this.contents;
    this.contents = [this.contents[0]];
    for (n = 1; n < contents.length; n++) {
        contents[n].row -= 1;
        debug('Shifting ' + new String(contents[n].id) + ' up.');
        if (contents[n].row >= 0) {
            this.contents.push(contents[n]);
        } else {
            this.element.removeChild(contents[n]);
            debug('It is off the screen!');
        }
    }

    this.terrain.push(terrain);
    this.terrain.shift();

    for (n = 0; n < terrain.length; n++) {
        if (items[n]) {
            for (m = 0; m < items[n].length; m++) {
                var itemNode = createItemTile(VIEWPORT_X - 1, n, m, items[n][m]);
                this.contents.push(itemNode);
                this.element.appendChild(itemNode);
            }
        }
    }

    this.redraw();
};



function GameMap(terrain) {
    this.terrain = terrain;
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

    notify(introductoryInstructions);
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
    document.getElementById(tileId).src = mapTileImageSource(kind);
};

function createMapTile(row, col, kind) {
    /* Create a completely initialized map tile at the given location
     * and with the given terrain type.
     */
    var image = document.createElement('img');
    image.src = mapTileImageSource(kind);
    image.height = TILE_HEIGHT_PX;
    image.width = TILE_WIDTH_PX;

    var pos = absolutePositionFromCoordinates(row, col);

    var tile = document.createElement('div');
    tile.id = mapTileNodeId(col, row);
    setNodePosition(tile, pos[0], pos[1]);
    tile.appendChild(image);

    return tile;
};

function itemTileImageSource(kind) {
    notify('Creating ' + kind);
    return '/static/radical/' + kind + '.png';
}

function createItemTile(row, col, idx, kind) {
    /* Create a completely initialized item tile at the given
     * location.
     */
    notify('Creating an item tile at ' + row + ' ' + col + ' of type ' + kind);

    var image = document.createElement('img');
    image.src = itemTileImageSource(kind);
//     image.height = TILE_HEIGHT_PX;
//     image.width = TILE_WIDTH_PX;

    var pos = absoluteObjectPositionFromCoordinates(row, col);
    var tile = document.createElement('span');
    tile.id = 'item-' + row + '-' + col + '-' + idx;
    setNodePosition(tile, pos[0], pos[1]);
    tile.style.zIndex = row + 1;
    tile.appendChild(image);

    tile.row = row;
    tile.col = col;

    return tile;
}

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
    node.style.cssText = 'position: absolute; z-index: 2';
    charImage.src = charImageURL;
    charImage.height = OBJECT_HEIGHT_PX;
    charImage.width = OBJECT_WIDTH_PX;

    charMessage.style.cssText = 'background-color: white; opacity: 100; visibility: hidden; border-style: solid; border-color: red';

    node.appendChild(charMessage);
    node.appendChild(charImage);

    return node;
};

function moveCharacterTile(charNode, row, col) {
    var pos = absoluteObjectPositionFromCoordinates(row, col);
    setNodePosition(charNode, pos[0], pos[1]);
    charNode.row = row;
    if (col != charNode.col) {
        charNode.col = col;
        charNode.style.zIndex = col;
    }
};

function characterId(charId) {
    return 'character-' + charId;
};

function eraseCharacter(charId) {
    var node = document.getElementById(characterId(charId));
    if (node) {
        debug('Erasing character ' + charId + '.');
        theMap.element.removeChild(node);
        for (n = 0; n < theMap.contents.length; n++) {
            if (theMap.contents[n] == node) {
                debug('Removing ' + new String(theMap.contents[n].id) + ' from the map.');
                debug('Contents is now ' + new String(theMap.contents));
                theMap.contents.splice(n, 1);
                break;
            }
        }
    } else {
        debug('Bogus erase request: ' + charId + '.');
    }
};


function moveCharacter(charId, row, col, charImage) {
    var node = document.getElementById(characterId(charId));
    if (!node) {
        node = createCharacterTile(characterId(charId), characterTileImageSource(charImage));
        theMap.element.appendChild(node);
        theMap.contents.push(node);
        debug('Creating a new character ' + charId);
        debug('Contents is now ' + new String(theMap.contents));
    }
    debug('Moving ' + charId + ' to row ' + new String(row) + ', ' + new String(col) + '.');
    moveCharacterTile(node, row, col);
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
    notify(charId + ' says ' + message);
};


function addInventoryItem(itemId, kind) {
    var itemsNode = document.getElementById('inventory-items');
    var newItem = document.createElement('img');
    newItem.id = 'inventory-' + itemId;
    newItem.src = itemTileImageSource(kind);
    itemsNode.appendChild(newItem);
}

function removeInventoryItem(itemId) {
    var itemNode = document.getElementById('inventory-' + itemId);
    itemNode.parentNode.removeChild(itemNode);
}

function displayInventory() {
    var imageNode = document.getElementById('inventory-image');
    var itemsNode = document.getElementById('inventory-items');

    imageNode.style.visibility = 'hidden';
    itemsNode.style.visibility = 'visible';
}

function hideInventory() {
    var imageNode = document.getElementById('inventory-image');
    var itemsNode = document.getElementById('inventory-items');

    imageNode.style.visibility = 'visible';
    itemsNode.style.visibility = 'hidden';
}


function onKeyPress(event) {
    /* Capture keystrokes and report them to the server.
     */
    // debug(strvars(event));

    if (event.keyCode == event.DOM_VK_LEFT) {
        server.handle('leftArrow', event.ctrlKey);
        event.cancelBubble = true;
    } else if (event.keyCode == event.DOM_VK_RIGHT) {
        server.handle('rightArrow', event.ctrlKey);
        event.cancelBubble = true;
    } else if (event.keyCode == event.DOM_VK_UP) {
        server.handle('upArrow', event.ctrlKey);
        event.cancelBubble = true;
    } else if (event.keyCode == event.DOM_VK_DOWN) {
        server.handle('downArrow', event.ctrlKey);
        event.cancelBubble = true;
    } else if (event.which == 39) {
        // Single-quote
        debug("Doing it");
        var form = document.getElementById('input-form');
        form.style.visibility = 'visible';
        form.firstChild.nextSibling.focus();
        event.cancelBubble = true;
    } else {
        server.handle('keyPress',
                      String.fromCharCode(event.which),
                      event.altKey, event.ctrlKey, event.metaKey,
                      event.shiftKey);
    }

    if (event.keyCode == event.DOM_VK_BACK_SPACE) {
        return false;
    }
    return true;
};

function inputSubmitted(event, form, inputNode) {
    var message = inputNode.value;

    inputNode.value = '';
    server.handle('sendMessage', message);
    inputNode.blur();

    form.style.visibility = 'hidden';

    return false;
}

document.onkeypress = onKeyPress;


var radical_oldOnLoad = window.onload;
function radical_onLoad() {
    if (radical_oldOnLoad) {
        radical_oldOnLoad();
    }

    notification = document.getElementById('notification');
    setNodePosition(notification, MAP_LEFT_PX + (TILE_WIDTH_PX * VIEWPORT_X), MAP_TOP_PX);

    inputForm = document.getElementById('input-form');
    setNodePosition(inputForm, MAP_LEFT_PX, MAP_TOP_PX + (TILE_HEIGHT_PX * VIEWPORT_Y));

    inventoryNode = document.getElementById('inventory');
    setNodePosition(inventoryNode, MAP_LEFT_PX + (TILE_WIDTH_PX * VIEWPORT_X), MAP_TOP_PX + (TILE_HEIGHT_PX * (VIEWPORT_Y - 1)));
}
window.onload = radical_onLoad;

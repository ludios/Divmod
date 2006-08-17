
// Width and height, in tiles, of the viewport onto the world map
var VIEWPORT_X = 16;
var VIEWPORT_Y = 16;

// Reference to the single instance of GameMap
var theMap = null;

// Pixel position of the top, left corner of the map area
var MAP_TOP_PX = 75;
var MAP_LEFT_PX = 175;

// Pixel size of each tile
var TILE_WIDTH_PX = 48;
var TILE_HEIGHT_PX = 24;

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
    for (var e in obj) {
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
function square_absolutePositionFromCoordinates(row, col) {
    return [MAP_LEFT_PX + row * TILE_WIDTH_PX, MAP_TOP_PX + col * TILE_HEIGHT_PX];
};

// col,row                      col-row             col+row
//              1,1                      0                  2
//           1,2   2,1                 -1  1              3   3
//        1,3   2,2   3,1            -2  0   2          4   4   4
//     1,4   2,3   3,2   4,1       -3  -1  1   3      5   5   5   5
//  1,5   2,4   3,3   4,2   5,1  -4  -2  0   2   4  6   6   6   6   6
//     2,5   3,4   4,3   5,2       -3  -1  1   3      7   7   7   7
//        3,5   4,4   5,3            -2  0   2          8   8   8
//           4,5   5,4                 -1  1              9   9
//              5,5                      0                 10
function diamond_absolutePositionFromCoordinates(row, col) {
    var baseX = MAP_LEFT_PX + (VIEWPORT_Y / 2 * TILE_WIDTH_PX);
    var baseY = MAP_TOP_PX;

    var pixelX = (col - row) * TILE_WIDTH_PX;
    var pixelY = (col + row) * TILE_HEIGHT_PX;

    var result = [MAP_LEFT_PX + pixelX + baseX, MAP_TOP_PX + pixelY + baseY];

    debug('Coordinates for ' + row + ' ' + col + ':' + pixelX + ' ' + pixelY);
    return result;
};

var absolutePositionFromCoordinates = diamond_absolutePositionFromCoordinates;

function GameMap_erase() {
    this.element.innerHTML = '';
};

function GameMap_redraw() {
    var idx = 0;
    for (var row = 0; row < this.terrain.length; row++) {
        for (var col = 0; col < this.terrain[row].length; col++) {
            var imgSrc = mapTileImageSource(this.terrain[row][col]);
            this.tiles[idx].firstChild.src = imgSrc;
            idx++;
        }
    }

    var pos = null;
    for (var n = 0; n < this.contents.length; n++) {
        var obj = this.contents[n];
        var pos = absolutePositionFromCoordinates(obj.row, obj.col);
        setNodePosition(obj, pos[0], pos[1]);
        debug("Rendering " + new String(obj.id) + " at " + pos.join(', '));
    }
};

function GameMap_insertTopRow(terrain, items) {
    /* Move everything on the screen down one.  Insert the given
     * terrain in the new, empty row at the top.
     */
    debug('Insert top row: ' + JSON.stringify(items));

    var contents = this.contents;
    this.contents = [this.contents[0]];
    for (var n = 1; n < contents.length; n++) {
        contents[n].col += 1;
        debug('Shifting ' + new String(contents[n].id) + ' right.');
        if (contents[n].col < VIEWPORT_Y) {
            contents[n].style.zIndex = objectZIndex(contents[n].row, contents[n].col);
            this.contents.push(contents[n]);
        } else {
            this.element.removeChild(contents[n]);
            debug('It is off the screen!');
        }
    }

    for (var n = 0; n < terrain.length; n++) {
        this.terrain[n].unshift(terrain[n]);
        this.terrain[n].pop();
        if (items[n]) {
            for (var m = 0; m < items[n].length; m++) {
                this.addObject(n, 0, items[n][m]);
            }
        }
    }
    this.redraw();
};

function GameMap_insertBottomRow(terrain, items) {
    /* Opposite of insertTopRow
     */
    debug('Insert bottom row: ' + JSON.stringify(items));

    var contents = this.contents;
    this.contents = [this.contents[0]];
    for (var n = 1; n < contents.length; n++) {
        contents[n].col -= 1;
        debug('Shifting ' + new String(contents[n]) + ' left.');
        if (contents[n].col >= 0) {
            contents[n].style.zIndex = objectZIndex(contents[n].row, contents[n].col);
            this.contents.push(contents[n]);
        } else {
            this.element.removeChild(contents[n]);
            debug('It is off the screen!');
        }
    }

    for (var n = 0; n < terrain.length; n++) {
        this.terrain[n].push(terrain[n]);
        this.terrain[n].shift();
        if (items[n]) {
            for (var m = 0; m < items[n].length; m++) {
                this.addObject(n, VIEWPORT_Y - 1, items[n][m]);
            }
        }
    }
    this.redraw();
};

function GameMap_insertLeftColumn(terrain, items) {
    /* Move everything to the right and insert the given terrain in the
     * new empty column.
     */
    debug('Insert left column: ' + JSON.stringify(items));

    var contents = this.contents;
    this.contents = [this.contents[0]];
    for (var n = 1; n < contents.length; n++) {
        debug('Shifting ' + new String(contents[n].id) + ' down.');
        contents[n].row += 1;
        if (contents[n].row < VIEWPORT_Y) {
            contents[n].style.zIndex = objectZIndex(contents[n].row, contents[n].col);
            this.contents.push(contents[n]);
        } else {
            this.element.removeChild(contents[n]);
            debug('It is off the screen!');
        }
    }

    this.terrain.unshift(terrain);
    this.terrain.pop();

    for (var n = 0; n < terrain.length; n++) {
        if (items[n]) {
            for (var m = 0; m < items[n].length; m++) {
                this.addObject(0, n, items[n][m]);
            }
        }
    }

    this.redraw();
};


function GameMap_insertRightColumn(terrain, items) {
    /* Move everything to the left and insert the given terrain in the
     * new empty column.
     */
    debug('Insert right column: ' + JSON.stringify(items));

    var contents = this.contents;
    this.contents = [this.contents[0]];
    for (var n = 1; n < contents.length; n++) {
        contents[n].row -= 1;
        debug('Shifting ' + new String(contents[n].id) + ' up.');
        if (contents[n].row >= 0) {
            contents[n].style.zIndex = objectZIndex(contents[n].row, contents[n].col);
            this.contents.push(contents[n]);
        } else {
            this.element.removeChild(contents[n]);
            debug('It is off the screen!');
        }
    }

    this.terrain.push(terrain);
    this.terrain.shift();

    for (var n = 0; n < terrain.length; n++) {
        if (items[n]) {
            for (var m = 0; m < items[n].length; m++) {
                this.addObject(VIEWPORT_X - 1, n, items[n][m]);
            }
        }
    }

    this.redraw();
};

var objectCounter = 0;
function GameMap_addObject(x, y, obj) {
    var itemNode = createItemTile(x, y, objectCounter, obj);
    objectCounter += 1;
    this.contents.push(itemNode);
    this.element.appendChild(itemNode);
}

function GameMap(terrain) {
    this.terrain = terrain;
    this.width = terrain.length;
    this.height = terrain[0].length;
    this.contents = [];

    this.element = document.getElementById('map-node');

    this.tiles = [];
    for (var row = 0; row < this.terrain.length; row++) {
        for (var col = 0; col < this.terrain[row].length; col++) {
            var tile = createMapTile(row, col, this.terrain[row][col]);
            this.tiles[this.tiles.length] = tile;
            this.element.appendChild(tile);
        }
    }

    this.erase = GameMap_erase;
    this.redraw = GameMap_redraw;
    this.addObject = GameMap_addObject;
    this.insertTopRow = GameMap_insertTopRow;
    this.insertBottomRow = GameMap_insertBottomRow;
    this.insertLeftColumn = GameMap_insertLeftColumn;
    this.insertRightColumn = GameMap_insertRightColumn;

    notify(introductoryInstructions);
};

function initializeMap(terrain) {
    theMap = new GameMap(terrain);
}

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

function objectZIndex(row, col) {
    return (theMap.width * col) + row;
}

function characterZIndex(row, col) {
    return (theMap.width * col+1) + (row+1);
}

function createMapTile(row, col, kind) {
    /* Create a completely initialized map tile at the given location
     * and with the given terrain type.
     */
    var image = document.createElement('img');
    image.src = mapTileImageSource(kind);

    // XXX These multipliers should /not/ be here - the images need to be pre-scaled.
//     image.height = TILE_HEIGHT_PX * 2.07;
//     image.width = TILE_WIDTH_PX * 2.07;

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

    var image = document.createElement('img');
    image.src = itemTileImageSource(kind);
//     image.height = TILE_HEIGHT_PX;
//     image.width = TILE_WIDTH_PX;

    var pos = absolutePositionFromCoordinates(row, col);
    var tile = document.createElement('span');
    tile.id = 'item-' + row + '-' + col + '-' + idx;
    setNodePosition(tile, pos[0], pos[1]);
    tile.style.zIndex = objectZIndex(row, col);
    tile.appendChild(image);

    tile.row = row;
    tile.col = col;

    notify('Creating an item tile at ' + row + ' ' + col + ' of type ' + kind + ' with zIndex ' + tile.style.zIndex);

    return tile;
}

function characterTileImageSource(image) {
    return '/static/radical/' + image + '.png';
};

function createCharacterTile(charName, charImageURL) {
    var node = document.createElement('span');
    var charImage = document.createElement('img');
    var charMessage = document.createElement('div');
    var charLabel = document.createElement('div');

    node.id = characterId(charName);
    node.style.position = 'absolute';

    charImage.src = charImageURL;
    charImage.height = OBJECT_HEIGHT_PX;
    charImage.width = OBJECT_WIDTH_PX;

    charMessage.style.visibility = 'hidden';
    charMessage.style.backgroundColor = 'white';
    charMessage.style.opacity = 0.6;
    charMessage.style.borderStyle = 'solid';
    charMessage.style.borderColor = 'white';

    charLabel.appendChild(document.createTextNode(charName));

    node.appendChild(charMessage);
    node.appendChild(charImage);
    node.appendChild(charLabel);

    return node;
};

function moveCharacterTile(charNode, row, col) {
    var pos = absolutePositionFromCoordinates(row, col);
    setNodePosition(charNode, pos[0], pos[1]);
    charNode.row = row;
    charNode.col = col;
    charNode.style.zIndex = characterZIndex(row, col);
};

function characterId(charId) {
    return 'character-' + charId;
};

function eraseCharacter(charName) {
    var node = document.getElementById(characterId(charName));
    if (node) {
        debug('Erasing character ' + charName + '.');
        theMap.element.removeChild(node);
        for (var n = 0; n < theMap.contents.length; n++) {
            if (theMap.contents[n] == node) {
                debug('Removing ' + new String(theMap.contents[n].id) + ' from the map.');
                debug('Contents is now ' + new String(theMap.contents));
                theMap.contents.splice(n, 1);
                break;
            }
        }
    } else {
        debug('Bogus erase request: ' + charName + '.');
    }
};


function moveCharacter(charName, row, col, charImage) {
    var node = document.getElementById(characterId(charName));
    if (!node) {
        node = createCharacterTile(charName, characterTileImageSource(charImage));
        theMap.element.appendChild(node);
        theMap.contents.push(node);
        debug('Creating a new character ' + charName);
        debug('Contents is now ' + new String(theMap.contents));
    }
    debug('Moving ' + charName + ' to row ' + new String(row) + ', ' + new String(col) + '.');
    moveCharacterTile(node, row, col);
};

function appendMessage(charName, message) {
    var node = document.getElementById(characterId(charName));
    var messageNode = node.firstChild;

    messageNode.innerHTML = message;
    messageNode.style.visibility = 'visible';
    window.setTimeout(function() {
                          if (messageNode.innerHTML == message) {
                              messageNode.style.visibility = 'hidden';
                          } else {
                              notify('Text changed from ' + message + ' to ' + messageNode.innerHTML + ' so not hiding.');
                          }
                      }, 10000);
    notify(charName + ' says ' + message);
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


var ignoringArrowKeys = false;

var arrowFunctions = null;

function onKeyPress(event) {
    /* Capture keystrokes and report them to the server.
     */

    if (arrowFunctions == null) {
        arrowFunctions = [];
        arrowFunctions[event.DOM_VK_LEFT] = 'leftArrow';
        arrowFunctions[event.DOM_VK_RIGHT] = 'rightArrow';
        arrowFunctions[event.DOM_VK_UP] = 'upArrow';
        arrowFunctions[event.DOM_VK_DOWN] = 'downArrow';
    }

    var arrowFunc = arrowFunctions[event.keyCode];
    if (arrowFunc != undefined) {
        if (!ignoringArrowKeys) {
            server.handle(arrowFunc, event.ctrlKey);
            ignoringArrowKeys = true;
            setTimeout(function() { ignoringArrowKeys = false; }, 20);
        }
        return false;
    } else if (event.which == 39) {
        // Single-quote
        debug("Doing it");
        var form = document.getElementById('input-form');
        form.style.visibility = 'visible';
        form.firstChild.nextSibling.focus();
        return false;
    } else if (event.keyCode == event.DOM_VK_BACK_SPACE) {
        return false;
    } else {
        server.handle('keyPress',
                      String.fromCharCode(event.which),
                      event.altKey, event.ctrlKey, event.metaKey,
                      event.shiftKey);
        return true;
    }
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

    var notification = document.getElementById('notification');
    setNodePosition(notification, MAP_LEFT_PX + (TILE_WIDTH_PX * VIEWPORT_X * 1.5), MAP_TOP_PX);

    var inputForm = document.getElementById('input-form');
    setNodePosition(inputForm, MAP_LEFT_PX, MAP_TOP_PX + (TILE_HEIGHT_PX * VIEWPORT_Y * 2));
}
window.onload = radical_onLoad;

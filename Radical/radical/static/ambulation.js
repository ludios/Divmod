
var VIEWPORT_X = 8;
var VIEWPORT_Y = 8;

var theMap = null;

var messageCount = 0;

var introductoryInstructions = (
    'Welcome to Radical.  Use the arrow keys to move around.  ' +
    'Use \' to focus the chat box.  Have fun!');

function debug(message) {
    if (false) {
        notify(message);
    }
}

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

function strvars(obj) {
    var accum = [];
    for (e in obj) {
        accum.push(e + ': ' + obj[e]);
    }
    return '{' + accum.join(', ') + '}';
}

function mapTileImageSource(kind) {
    /* Return the URL for the image representing the terrain of the
     * given kind.
     */
    return '/static/radical/' + kind + '.png';
};

function absolutePositionFromCoordinates(row, col) {
    return [175 + row * 64, 75 + col * 64];
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

    var pos = null;
    for (var n = 0; n < this.contents.length; n++) {
        obj = this.contents[n];
        pos = absolutePositionFromCoordinates(obj.row, obj.col);
        obj.style.left = new String(pos[0]) + "px";
        obj.style.top = new String(pos[1]) + "px";
        debug("Rendering " + new String(obj.id) + " at " + obj.style.cssText);
    }
};

function GameMap_insertTopRow(terrain) {
    /* Move everything on the screen down one.  Insert the given
     * terrain in the new, empty row at the top.
     */
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
    }
    this.redraw();
};

function GameMap_insertBottomRow(terrain) {
    /* Opposite of insertTopRow
     */
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
    }
    this.redraw();
};

function GameMap_insertLeftColumn(terrain) {
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
    this.redraw();
};


function GameMap_insertRightColumn(terrain) {
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
    document.getElementById(tileId).setAttribute('src', mapTileImageSource(kind));
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
    tile.style.left = new String(pos[0]) + 'px';
    tile.style.top = new String(pos[1]) + 'px';
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
    node.style.cssText = 'position: absolute; z-index: 2';
    charImage.src = charImageURL;

    charMessage.style.cssText = 'background-color: white; opacity: 100; visibility: hidden; border-style: solid; border-color: red';

    node.appendChild(charMessage);
    node.appendChild(charImage);

    return node;
};

function moveCharacterTile(charNode, row, col) {
    var pos = absolutePositionFromCoordinates(row, col);
    charNode.style.position = 'absolute';
    charNode.style.left = new String(pos[0]) + 'px';
    charNode.style.top = new String(pos[1]) + 'px';
    charNode.row = row;
    charNode.col = col;
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



function onKeyPress(event) {
    /* Capture keystrokes and report them to the server.
     */
    // debug(strvars(event));

    if (event.keyCode == event.DOM_VK_LEFT) {
        server.handle('leftArrow');
    } else if (event.keyCode == event.DOM_VK_RIGHT) {
        server.handle('rightArrow');
    } else if (event.keyCode == event.DOM_VK_UP) {
        server.handle('upArrow');
    } else if (event.keyCode == event.DOM_VK_DOWN) {
        server.handle('downArrow');
    } else if (event.which == 39) {
        // Single-quote
        debug("Doing it");
        var form = document.getElementById('input-form');
        debug(form.firstChild.nextSibling);
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

function inputSubmitted(event, inputNode) {
    var message = inputNode.value;

    inputNode.value = '';
    server.handle('sendMessage', message);
    inputNode.blur();

    return false;
}

document.onkeypress = onKeyPress;

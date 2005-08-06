
function GameMap_erase() {
    this.element.innerHTML = '';
};

function GameMap_redraw() {
    for (row = 0; row < this.terrain.length; row++) {
        for (col = 0; col < this.terrain[row].length; col++) {
            tile = createMapTile(row, col, this.terrain[row][col]);
            this.element.appendChild(tile);
        }
    }
};

function GameMap(terrain) {
    this.terrain = terrain
    this.width = terrain.length;
    this.height = terrain[0].length;

    this.element = document.getElementById('map-node');

    this.erase = GameMap_erase;
    this.redraw = GameMap_redraw;
};

var theMap = null;

function mapTileImageSource(kind) {
    /* Return the URL for the image representing the terrain of the
     * given kind.
     */
    return '/static/radical/' + kind + '.png';
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

    var tile = document.createElement('div');
    tile.setAttribute('id', mapTileNodeId(col, row));
    tile.style.position = 'absolute';
    tile.style.top = new String(75 + row * 64) + 'px';
    tile.style.left = new String(175 + col * 64) + 'px';
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

function insertTopRow(terrain) {
    /* Move everything on the screen down one.  Insert the given
     * terrain in the new, empty row at the top.
     */
    theMap.terrain.unshift(terrain);
    theMap.terrain.pop();
    theMap.redraw();
};

function insertBottomRow(terrain) {
    /* Opposite of insertTopRow
     */
    theMap.terrain.push(terrain);
    theMap.terrain.shift();
    theMap.redraw();
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



// import Divmod
// import Radical


// Width and height, in tiles, of the viewport onto the world map
var VIEWPORT_X = 16;
var VIEWPORT_Y = 16;

// Pixel position of the top, left corner of the map area
var MAP_TOP_PX = 75;
var MAP_LEFT_PX = 0;

// Pixel size of each tile
var TILE_WIDTH_PX = 55;
var TILE_HEIGHT_PX = 64 / Math.sqrt(2);

// Pixel size of each object which can occupy a tile
var OBJECT_WIDTH_PX = 128;
var OBJECT_HEIGHT_PX = 128;

Radical.Geometry = {};

Radical.Geometry.Viewport = Divmod.Class.subclass('Radical.Geometry.Viewport');
Radical.Geometry.Viewport.methods(
    function __init__(self, top, left, width, height) {
        /*
         * Create a new viewport object at the given absolute world coordinates
         * with the given size.
         */
        self.top = top;
        self.left = left;
        self.width = width;
        self.height = height;
    },

    function pixelPositionFromViewportCoordinates(self, col, row) {
        var baseX = MAP_LEFT_PX + (VIEWPORT_Y / 2 * TILE_WIDTH_PX);
        var baseY = MAP_TOP_PX;

        var pixelX = col * TILE_WIDTH_PX;
        var pixelY = row * TILE_HEIGHT_PX;

        var result = {'left': MAP_LEFT_PX + pixelX + baseX,
                      'bottom': MAP_TOP_PX + pixelY + baseY};

        return result;
    },

    function pixelPositionFromWorldCoordinates(self, col, row) {
        /*
         * Turn the absolute world coordinates into viewport-local coordinates.
         */
        var result = self.pixelPositionFromViewportCoordinates(col - self.left, row - self.top);
        if (row % 2) {
            result.left += TILE_WIDTH_PX / 2;
        }
        return result;
    },

    function setTerrainImagePosition(self, img, col, row) {
        /*
         * Position the given terrain image at the given viewport-relative
         * coordinates.
         */
        var pos = self.pixelPositionFromViewportCoordinates(col, row);
        pos.bottom -= img.height;
        if ((self.top + row) % 2) {
            pos.left += TILE_WIDTH_PX / 2;
        }
        img.style.left = pos.left + 'px';
        img.style.top = pos.bottom + 'px';
    },

    function setItemImagePosition(self, img, col, row) {
        /*
         * Position the given item(/player/etc - not terrain) image at the
         * given absolute world coordinates.
         */
        var pos = self.pixelPositionFromWorldCoordinates(col, row);
        pos.left += img.width / 2;
        pos.bottom -= img.height;

        img.style.left = pos.left + 'px';
        img.style.top = pos.bottom + 'px';
    });

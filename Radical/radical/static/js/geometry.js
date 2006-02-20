
// import Divmod
// import Radical


// Width and height, in tiles, of the viewport onto the world map
var VIEWPORT_X = 16;
var VIEWPORT_Y = 16;

// Pixel position of the top, left corner of the map area
var MAP_TOP_PX = 75;
var MAP_LEFT_PX = 175;

// Pixel size of each tile
var TILE_WIDTH_PX = 48;
var TILE_HEIGHT_PX = 24;

// Pixel size of each object which can occupy a tile
var OBJECT_WIDTH_PX = 128;
var OBJECT_HEIGHT_PX = 128;

Radical.SquareGeometry = Divmod.Class.subclass('Radical.SquareGeometry');
Radical.SquareGeometry.methods(

    // Pixel position of a tile at the given tile-based coordinate
    function absolutePositionFromCoordinates(self, row, col) {
        var result = {'left': MAP_LEFT_PX + row * TILE_WIDTH_PX,
                      'top': MAP_TOP_PX + col * TILE_HEIGHT_PX};
        return result;
    });


Radical.IsometricGeometry = Divmod.Class.subclass('Radical.IsometricGeometry');
Radical.IsometricGeometry.methods(
    // col,row                      col-row             col+row              row-col
    //              1,1                      0                  2                   0
    //           1,2   2,1                 -1  1              3   3               1  -1
    //        1,3   2,2   3,1            -2  0   2          4   4   4           2   0  -2
    //     1,4   2,3   3,2   4,1       -3  -1  1   3      5   5   5   5       3   1  -1  -3
    //  1,5   2,4   3,3   4,2   5,1  -4  -2  0   2   4  6   6   6   6   6   4   2   0  -2  -4
    //     2,5   3,4   4,3   5,2       -3  -1  1   3      7   7   7   7       3   1  -1  -3
    //        3,5   4,4   5,3            -2  0   2          8   8   8           2   0  -2
    //           4,5   5,4                 -1  1              9   9               1  -1
    //              5,5                      0                 10                   0

    function absolutePositionFromCoordinates(self, row, col) {
        var baseX = MAP_LEFT_PX + (VIEWPORT_Y / 2 * TILE_WIDTH_PX);
        var baseY = MAP_TOP_PX;

        var pixelX = (row - col) * TILE_WIDTH_PX;
        var pixelY = (col + row) * TILE_HEIGHT_PX;

        var result = {'left': MAP_LEFT_PX + pixelX + baseX,
                      'top': MAP_TOP_PX + pixelY + baseY};

        return result;
    });

Radical.Geometry = new Radical.IsometricGeometry();

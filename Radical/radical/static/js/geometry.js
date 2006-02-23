
// import Divmod
// import Radical


// Pixel size of each tile
var TILE_WIDTH_PX = 55;
var TILE_HEIGHT_PX = 64 * 0.75;

// Pixel size of each object which can occupy a tile
var OBJECT_WIDTH_PX = 128;
var OBJECT_HEIGHT_PX = 128;

Radical.Geometry = {};

Radical.Geometry.Viewport = Divmod.Class.subclass('Radical.Geometry.Viewport');
Radical.Geometry.Viewport.methods(
    /*
     * Create a new viewport object at the given absolute world coordinates
     * with the given size.
     *
     * model will be an object with the following methods:
     *
     *     getTerrainKind(modelx, modely) -> kind of terrain
     *
     *     getEntity(modelx, modely) -> kind of non-terrain thing
     *
     */
    function __init__(self, model, x, y, width, height) {
        self.model = model;
        self.x = x;
        self.y = y;
        self.width = width;
        self.height = height;

        self.evenNode = document.createElement('span');
        self.oddNode = document.createElement('span');

        self.evenNode.style.display = 'none';
        self.oddNode.style.display = 'none';

        /*
         * An Array of img tags representing the currently visible terrain.
         */
        self.visibleTerrainImagesEven = self._initializeRenderBuffer(self.evenNode, self.y % 2);


        /*
         * An Array of img tags representing the currently visible terrain.
         */
        self.visibleTerrainImagesOdd = self._initializeRenderBuffer(self.oddNode, (self.y + 1) % 2);
    },

    /*
     * Hahahahahahaha.  I'm so funny.
     */
    function _initializeRenderBuffer(self, parentNode, twiddleAmount) {
        var result = new Array(self.width * self.height);
        for (var x = 0; x < self.width; ++x) {
            for (var y = 0; y < self.height; ++y) {
                var img = result[y * self.width + x] = document.createElement('img');
                img.src = Radical.Artwork.terrainLocation('barren');
                img.style.position = 'absolute';
                img.onload = (function(img, x, y) {
                    return function() {
                        img.onload = null;

                        /*
                         * This is a bit of a hack, eh?
                         */
                        self.y += twiddleAmount;
                        self.setImagePosition(img, x, y + twiddleAmount);
                        self.y -= twiddleAmount;

                        parentNode.appendChild(img);
                    };
                })(img, self.x + x, self.y + y);
            }
        }
        return result;
    },

    function visible(self, x, y) {
        return (x >= self.x && x < self.x + self.width && y >= self.y && y < self.y + self.height);
    },

    function paint(self, viewx, viewy, vieww, viewh) {
        var before = new Date();
        /*
         * Redraw the part of the screen represented by the rectangle with
         * top-left corner at (self.x + viewx, self.y + viewy) and bottom right
         * corner at (self.x + viewx + vieww, self.y + viewy + viewh).
         *
         */
        if (viewx == undefined) {
            viewx = 0;
        }
        if (viewy == undefined) {
            viewy = 0;
        }
        if (vieww == undefined) {
            vieww = self.width;
        }
        if (viewh == undefined) {
            viewh = self.height;
        }

        var images, flipin, flipout;
        if (self.y % 2) {
            images = self.visibleTerrainImagesOdd;
            flipin = self.oddNode;
            flipout = self.evenNode;
        } else {
            images = self.visibleTerrainImagesEven;
            flipin = self.evenNode;
            flipout = self.oddNode;
        }

        for (var x = viewx; x < viewx + vieww; ++x) {
            for (var y = viewy; y < viewy + viewh; ++y) {
                var kind = self.model.getTerrainKind(self.x + x, self.y + y);
                var idx = y * self.width + x;
                if (kind != null) {
                    images[idx].src = Radical.Artwork.terrainLocation(kind);
                } else {
                    images[idx].src = Radical.Artwork.terrainLocation('barren');
                }
            }
        }

        flipin.style.display = '';
        flipout.style.display = 'none';

        var entities = self.model.getEntitiesWithin(self.x, self.y, self.width, self.height);
        Divmod.msg("Painting " + entities.length + " entities.");
        for (var i = 0; i < entities.length; ++i) {
            if (images[idx].style.top) {
                var idx = ((entities[i].y - self.y) * self.width + (entities[i].x - self.x));
                entities[i].img.style.left = images[idx].style.left;

                var terrainTop = images[idx].style.top;
                Divmod.msg("Terrain top is " + terrainTop.toSource());
                var topInt = terrainTop.slice(0, terrainTop.length - 2);
                Divmod.msg("Top int is " + topInt);
                var intint = parseInt(topInt);
                var realTopInt = intint + images[idx].height - entities[i].img.height;
                Divmod.msg("Setting it to " + (realTopInt + 'px').toSource());
                entities[i].img.style.top = realTopInt + 'px';
            }
        }

        var after = new Date();
        Divmod.msg("Paint took " + (after.valueOf() - before.valueOf()));
    },

    function pixelPositionFromViewportCoordinates(self, col, row) {
        var result = {
            x: col * TILE_WIDTH_PX + 250,
            y: row * TILE_HEIGHT_PX + 155};
        return result;
    },

    function pixelPositionFromWorldCoordinates(self, col, row) {
        /*
         * Turn the absolute world coordinates into viewport-local coordinates.
         */
        var result = self.pixelPositionFromViewportCoordinates(col - self.x, row - self.y);
        if (row % 2) {
            result.x += TILE_WIDTH_PX / 2;
        }
        return result;
    },

    function viewportCoordinatesFromPixelPosition(self, screenx, screeny) {
        var result = {
            x: Math.floor((screenx - 250) / TILE_WIDTH_PX),
            y: Math.floor((screeny - 155) / TILE_HEIGHT_PX)};
        if (result.x >= 0 && result.x < self.width && result.y >= 0 && result.y < self.height) {
            return result;
        }
        Divmod.msg("Picker from " + screenx + ", " + screeny + " result was out of bounds: " + result.toSource());
        return null;
    },

    function worldCoordinatesFromPixelPosition(self, screenx, screeny) {
        var result = self.viewportCoordinatesFromPixelPosition(screenx, screeny);
        if (result != null) {
            result.x += self.x;
            result.y += self.y;
        }
        return result;
    },

    /*
     * Position the given image at the given absolute world coordinates.
     */
    function setImagePosition(self, img, col, row) {
        if (self.visible(col, row)) {
            var pos = self.pixelPositionFromWorldCoordinates(col, row);

            /*
             * Do all the math before setting any attributes, since doing it in
             * between causes rendering artifacts.
             */
            if (img.height != undefined) {
                pos.y -= img.height;
            }
            pos.x = Math.floor(pos.x) + 'px';
            pos.y = Math.floor(pos.y) + 'px';
            img.style.left = pos.x;
            img.style.top = pos.y;
            img.style.display = '';
        } else {
            Divmod.msg("Hiding out-of-bounds image: " + col + ", " + row);
            img.style.display = 'none';
        }
    });

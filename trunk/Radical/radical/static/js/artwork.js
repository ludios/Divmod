
// import Divmod

// import Radical

Radical._Artwork = Divmod.Class.subclass('Radical._Artwork');
Radical._Artwork.methods(
    function terrainLocation(self, kind) {
        /* Return a string representing the URL at which the image for the
           indicated kind of terrain may be found. */
        return '/Radical/static/images/terrain/' + kind + '.png';
    },

    function playerLocation(self, kind) {
        /* Return a string representing the URL at which the image for the
           indicated player may be found. */
        return '/Radical/static/images/players/' + kind + '.png';
    });

Radical.Artwork = new Radical._Artwork();

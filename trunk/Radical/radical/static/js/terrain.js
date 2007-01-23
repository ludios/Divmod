
// import Nevow.Athena

// import Radical

Radical.Terrain.Editor = Nevow.Athena.Widget.subclass("Radical.Terrain.EditorWidget");
Radical.Terrain.Editor.methods(
    function setTerrainType(self, kind) {
        self.callRemote('setTerrainType', kind).addCallback(function(loc) {
            self.widgetParent.childWidgets[0].cacheTerrainInfo(loc[0], loc[1], kind);
            self.widgetParent.childWidgets[0].paint();
        });
    },

    function grass(self) {
        self.setTerrainType('grass');
    },

    function forest(self) {
        self.setTerrainType('forest');
    },

    function water(self) {
        self.setTerrainType('water');
    },

    function mountain(self) {
        self.setTerrainType('mountain');
    });

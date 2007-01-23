// import ClickChronicle

ClickChronicle.BookmarkList = Nevow.Athena.Widget.subclass('ClickChronicle.BookmarkList');

ClickChronicle.BookmarkList.methods(
    function loaded(self) {
        self.bookmarkTDB = Mantissa.TDB.Controller.get(
                                self.nodeByAttribute('athena:class', 'Mantissa.TDB.Controller'));
    },

    function onTagSelect(self, select) {
        var tag = select.childNodes[select.selectedIndex].value;
        self.callRemote('filterBookmarks', tag).addCallback(
            function(data) { self.bookmarkTDB._setTableContent(data[0]);
                             self.bookmarkTDB._setPageState.apply(self.bookmarkTDB, data[1]) }
        ).addErrback(alert);
    });

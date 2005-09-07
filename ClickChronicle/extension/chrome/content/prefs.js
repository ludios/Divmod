function showDialog( chrome ) {
    window.openDialog( chrome, -1, "chrome,centerscreen" )
}

function openPrefs() {
    showDialog( "chrome://clickchronicle/content/prefs.xul" )
}

function openIgnoreModify() {
    showDialog( "chrome://clickchronicle/content/ignore-modify.xul" );
}

function enable( eId ) {
    document.getElementById( eId ).disabled = false;
}

function activateModifiers() {
    enable("modifyIgnore");
    enable("deleteIgnore");
}

function getDataSource( element ) {
    var dsEnum = element.database.GetDataSources();
    while( dsEnum.hasMoreElements() ) {
        var source = dsEnum.getNext();
        source = source.QueryInterface(Components.interfaces.nsIRDFDataSource);
        if( source.URI != "rdf:localstore" )
            return source;
    }
}
    
var RDF = Components.classes["@mozilla.org/rdf/rdf-service;1"]
    .getService(Components.interfaces.nsIRDFService);

var RDFC = Components.classes["@mozilla.org/rdf/container-utils;1"]
    .getService(Components.interfaces.nsIRDFContainerUtils);

function modifyIgnore() {
    var ignoreListBox = document.getElementById("ignore-rules-tree");
    var selectedListItem = ignoreListBox.selectedItem;
    var uri = selectedListItem.getAttribute( "identifier" );
    var prefsDataSource = getDataSource( ignoreListBox );
    alert( ignoreListBox.builder.getResourceAtIndex ); 
    var seq = RDFC.MakeSeq(prefsDataSource, ignoreListBox.resource);
}
    

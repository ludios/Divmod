var RDF = Components.classes["@mozilla.org/rdf/rdf-service;1"]
            .getService( Components.interfaces.nsIRDFService );
    
var IO = Components.classes["@mozilla.org/network/io-service;1"]
            .getService( Components.interfaces.nsIIOService );
            
function recordableURI( URI ) {
    return URI.schemeIs("http") && (URI.userPass == "");
    /* todo: compare URI against user-supplied filters,
       and common sense stuff like ignoring visits to clickchronicle */
}

function HistoryObserver() {}

function modifyingNameProperty( property ) {
    var propURN = property.Value;
    return (propURN.slice( propURN.indexOf("#") + 1 ) == "Name");
}

function handleHistoryHit( source, property, target ) {
    if(modifyingNameProperty( property )) {
        var URI = source.Value;
        if(recordableURI(IO.newURI( URI, null, null ))) {
            var pageTitle = target.QueryInterface( Components.interfaces.nsIRDFLiteral ).Value;
            alert([ URI, pageTitle ]);
        }
    }
}

HistoryObserver.prototype = {
   
            
    onChange : function( DS, source, property, oldTarget, newTarget ) {
        handleHistoryHit( source, property, newTarget );
    },

    onAssert : function( DS, source, property, target ) {
        handleHistoryHit( source, property, target );
    }

}

function observeHistory() {
    var historyDS = RDF.GetDataSource("rdf:history");
    historyDS.AddObserver( new HistoryObserver() );
}

observeHistory();

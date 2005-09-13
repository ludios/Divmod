/* 
    caveats:
    - will not record cached pages 
        maybe good, maybe not.  users with frequently visited 
        pre-cached pages won't have these visits recorded.  i think
        the need for this will be obviated by the soon-to-be-added
        bookmark-transfer feature.  if it's important we can probably
        observe the cache manager and detect cache hits.
    - redirects:
        if www.google.com redirects to www.google.co.za, which should
        be recorded?  what about other status codes, like "not found",
        "forbidden", "temporarily unavailable"
    stuff to add, maybe:
    - make the recording toggle operate per-tab, so indiscretions can be
      perpetrated in a designated area
*/

var contentTypePrefixes = ["text/"];

var RDF = Components.classes["@mozilla.org/rdf/rdf-service;1"]
            .getService( Components.interfaces.nsIRDFService );
    
var IO = Components.classes["@mozilla.org/network/io-service;1"]
            .getService( Components.interfaces.nsIIOService );

var gPrefs = Components.classes["@mozilla.org/preferences-service;1"]
                .getService( Components.interfaces.nsIPrefService )
                    .getBranch( "extensions.ClickChronicle." );

var observerSvc = Components.classes["@mozilla.org/observer-service;1"]
                        .getService(Components.interfaces.nsIObserverService);

function recordableURI( URI ) {
    return URI.schemeIs("http") && (URI.userPass == "") && (!URI.host.match(/divmod|localhost/));
    /* todo: compare URI against user-supplied filters,
       and common sense stuff like ignoring visits to clickchronicle */
}
/* rdf:history observation */

function HistoryObserver() { this.queuedURIs = new Object() }

HistoryObserver.prototype = {
    /* we'll subclass QueryInterface so we can keep non-standard 
      instance methods when we're adapted */
    QueryInterface : function( iid ) {
        with( Components.interfaces )
            if(iid.equals( nsIObserver ) || iid.equals( nsISupports ))
                return this;
            else
                throw Components.results.NS_ERROR_NO_INTERFACE;
    },

    callOnTitleChange : function( URI, callback ) {
        if( URI in this.queuedURIs )
            return;
        this.queuedURIs[URI] = callback;
    },
    
    modifyingNameProperty : function( property ) {
        var propURN = property.Value;
        return (propURN.slice( propURN.indexOf("#") + 1 ) == "Name");
    },

    onAssert : function( DS, source, property, target ) {
        if(this.modifyingNameProperty( property )) {
            var thisURI = source.Value;
            if( thisURI in this.queuedURIs ) {
                var newTitle = target.QueryInterface( Components.interfaces.nsIRDFLiteral ).Value;
                this.queuedURIs[thisURI]( newTitle );
                delete( this.queuedURIs[thisURI] );
            } else { 
            }
        }
    },

    onChange : function( DS, source, property, ot, nt ) {
        if(this.modifyingNameProperty( property )) {
            var thisURI = source.Value;
            if( thisURI in this.queuedURIs ) {
                var newTitle = target.QueryInterface( Components.interfaces.nsIRDFLiteral ).Value;
                this.queuedURIs[thisURI]( newTitle );
                delete( this.queuedURIs[thisURI] );
            } else {
            }
        }
    }

}

/* see what we can do about modularizing this */
var historyDS = RDF.GetDataSource("rdf:history");
var historyObserver = new HistoryObserver();
historyDS.AddObserver( historyObserver );

/* http-on-examine-response observation */

function getNCResource( arcName ) {
    return RDF.GetResource("http://home.netscape.com/NC-rdf#" + arcName);
}

function historyEntryForURI( URI, historyDataSource ) {
    var globalHistory = historyDataSource
                         .QueryInterface( Components.interfaces.nsIGlobalHistory2 );
                         
    if(globalHistory.isVisited( URI )) {
        var urlArc = getNCResource( "URL" );
        var urlTarget = RDF.GetResource( URI.spec );
        
        /* nsGlobalHistory::GetSource segfaults if passed an nsIRDFLiteral as
        * the "target" argument, despite the API documentation */

        return historyDataSource.GetSource( urlArc, urlTarget, true );
    } 
}

function encode64(input) {
    /* taken from http://www.aardwulf.com/tutor/base64/base64.html */
    var keyStr = "ABCDEFGHIJKLMNOP" +
                 "QRSTUVWXYZabcdef" +
                 "ghijklmnopqrstuv" +
                 "wxyz0123456789+/" +
                 "=";

    var output = "";
    var chr1, chr2, chr3 = "";
    var enc1, enc2, enc3, enc4 = "";
    var i = 0;

    do {
        chr1 = input.charCodeAt(i++);
        chr2 = input.charCodeAt(i++);
        chr3 = input.charCodeAt(i++);

        enc1 = chr1 >> 2;
        enc2 = ((chr1 & 3) << 4) | (chr2 >> 4);
        enc3 = ((chr2 & 15) << 2) | (chr3 >> 6);
        enc4 = chr3 & 63;

        if (isNaN(chr2)) {
        enc3 = enc4 = 64;
        } else if (isNaN(chr3)) {
        enc4 = 64;
        }

        output = output + 
        keyStr.charAt(enc1) + 
        keyStr.charAt(enc2) + 
        keyStr.charAt(enc3) + 
        keyStr.charAt(enc4);
        chr1 = chr2 = chr3 = "";
        enc1 = enc2 = enc3 = enc4 = "";
    } while (i < input.length);
    return output;
}

function urlencode( str ) {
    str = escape( str );
    str = str.replace(/\\+/g, "%2B");
    return str.replace(/%20/g, "+");
}

function innoculate( str ) {
    return escape(encode64( str ));
}

var consoleService = Components.classes['@mozilla.org/consoleservice;1']
                               .getService(Components.interfaces.nsIConsoleService);

function recordHit( URI ) {
    /* urgh, it seems that when a page is requested for the first time,
     * mozilla makes a history entry listing the page title as a prettified
     * version of the url ("divmod.com" for "x.y.divmod.com/z")..once the
     * page has loaded, or on a repeat visit - i can't discern, the entry is
     * overwritten with the real page title.  so if it's a first visit, we
     * tell our rdf:history observer to call us back with the page title once 
     * the datasource has been updated, otherwise just send the reported title
     * to the server */
    var histDataSource = RDF.GetDataSource( "rdf:history" );
    consoleService.logStringMessage( "viable hit for " + URI.spec );
    var histEntry = historyEntryForURI( URI, histDataSource );
    var weHaveTitle = false;
    if( histEntry ) {
        var visitCount = histDataSource.GetTarget( histEntry, getNCResource("VisitCount"), true )
                            .QueryInterface( Components.interfaces.nsIRDFInt ).Value;
        if( 1 < visitCount )
            weHaveTitle = true;
    }
                            
    function logToServer( title ) {
        consoleService.logStringMessage( "*** recording " + URI.spec + " - (" + title + ")" );
        var recorderURL = gPrefs.getCharPref( "clickRecorderURL" );
        var req = new XMLHttpRequest()
        req.open( "GET", recorderURL+"?url="+innoculate(URI.spec)+"&title="+innoculate(title), true ); 
        req.send( null );
    }

    if( weHaveTitle ) {
        var pageTitle = histDataSource.GetTarget( histEntry, getNCResource("Name"), true )
                            .QueryInterface( Components.interfaces.nsIRDFLiteral ).Value;
        logToServer( pageTitle );
    } else 
        historyObserver.callOnTitleChange( URI.spec, logToServer );
}
     
function ResponseObserver() {}

ResponseObserver.prototype = {
    /* called upon receipt of http response headers */
    observe : function( subject, topic, data ) {
        var channel = subject.QueryInterface( Components.interfaces.nsIHttpChannel );
        /* this test will be true if the page-load is the direct result of
           user interaction, e.g. typed URL, link click, or HTTP redirect 
           arising from either of those - IOW it wont log stuff like iframes 
           or inline images */
        if( channel.loadFlags & channel.LOAD_INITIAL_DOCUMENT_URI ) {
            var URI = channel.URI.QueryInterface( Components.interfaces.nsIURI );
            if(recordableURI( URI )) {
                var ctype = channel.getResponseHeader("content-type");
                for( var i = 0; i < contentTypePrefixes.length; i++ ) {
                    var prefix = contentTypePrefixes[i];
                    if(ctype.slice( 0, prefix.length ) == prefix) {
                        recordHit( URI );
                        return;
                    }
                }
                consoleService.logStringMessage("ignoring URL " + URI.spec + " b/c of content-type: " + ctype);
            }
        }
    }
}

function makeToggle( observer, topic ) {
    var observing = false; // maybe we can infer this from the observer?
    return function() {
        if( observing )
            observerSvc.removeObserver( observer, topic );
        else
            observerSvc.addObserver( observer, topic, false );
        observing = !observing;
    }
}

toggleObserver = makeToggle( new ResponseObserver(), "http-on-examine-response" );
        
function toggleRecording() {
    toggleObserver(); 
    var label = document.getElementById("clickchronicle-status").firstChild;
    var enabled = (label.className == "enabled");
    label.className = enabled ? "disabled" : "enabled";
    label.value = enabled ? "Not Recording" : "Recording Clicks";
}

function overlayLoaded( event ) {
    if(gPrefs.getBoolPref( "enableOnStartup" ))
        toggleRecording();
    window.removeEventListener("load", overlayLoaded, true);
}
    
window.addEventListener("load", overlayLoaded, true);

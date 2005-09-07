/* http://fishbowl.pastiche.org/2003/05/28/the_ghetto_minipattern */

/* at the moment this code will just open up a dialog box displaying the URL,
   each time it encounters something it would like eventually send to the server */
   
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

var RDF = Components.classes["@mozilla.org/rdf/rdf-service;1"]
            .getService( Components.interfaces.nsIRDFService );
    
var IO = Components.classes["@mozilla.org/network/io-service;1"]
            .getService( Components.interfaces.nsIIOService );

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
            }
        }
    },

    onChange : function( DS, source, property, ot, nt ) {}

}

/* see what we can do about modularizing this */
var historyDS = RDF.GetDataSource("rdf:history");
var historyObserver = new HistoryObserver();
historyDS.AddObserver( historyObserver );

/* http-on-examine-response observation */

function recordableURI( URI ) {
    return URI.schemeIs("http") && (URI.userPass == "");
    /* todo: compare URI against user-supplied filters,
       and common sense stuff like ignoring visits to clickchronicle */
}

function getNCResource( arcName ) {
    return RDF.GetResource("http://home.netscape.com/NC-rdf#" + arcName);
}

function historyEntryForURI( URI, historyDataSource ) {
    /* this whole process is disturbing */
    var urlArc = getNCResource( "URL" );
    var urlTarget = RDF.GetResource( URI );
    
    /* nsGlobalHistory::GetSource segfaults if passed an nsIRDFLiteral as
     * the "target" argument, despite the API documentation */

    return historyDataSource.GetSource( urlArc, urlTarget, true );
}

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
    var histEntry = historyEntryForURI( URI.spec, histDataSource );
    var visitCount = histDataSource.GetTarget( histEntry, getNCResource("VisitCount"), true )
                        .QueryInterface( Components.interfaces.nsIRDFInt ).Value;
    
    function logToServer( title ) {
        /* well, it will soon log to the server */
        alert("logging: " + URI.spec + " title: " + title);
    }

    if( visitCount == 1 ) {
        historyObserver.callOnTitleChange( URI.spec, logToServer );
    } else {
        var pageTitle = histDataSource.GetTarget( histEntry, getNCResource("Name"), true )
                            .QueryInterface( Components.interfaces.nsIRDFLiteral ).Value;
        logToServer( pageTitle );
    }
}
     
function ResponseObserver() {}

ResponseObserver.prototype = {
    /* called upon receipt of http response headers */
    observe : function( subject, topic, data ) {
        var channel = subject.QueryInterface( Components.interfaces.nsIChannel );
        /* this test will be true if the page-load is the direct result of
           user interfaction, e.g. typed URL, link click, or HTTP redirect 
           arising from either of those - IOW it wont log stuff like iframes 
           or inline images */
        if( channel.loadFlags & channel.LOAD_INITIAL_DOCUMENT_URI ) {
            var URI = channel.URI.QueryInterface( Components.interfaces.nsIURI );
            if(recordableURI( URI ))
                recordHit( URI );
        }
    }
}

function makeToggle( observer, topic ) {
    var observerService = Components.classes["@mozilla.org/observer-service;1"]
                            .getService(Components.interfaces.nsIObserverService);
    var observing = false; // maybe we can infer this from the observer?
    return function() {
        if( observing )
            observerService.removeObserver( observer, topic );
        else
            observerService.addObserver( observer, topic, false );
        observing = !observing;
    }
}

toggleObserver = makeToggle( new ResponseObserver(), "http-on-examine-response" );
toggleObserver();
        
function toggleRecording() {
    var label = document.getElementById("clickchronicle-status").firstChild;
    var enabled = (label.className == "enabled");
    toggleObserver(); 
    label.className = enabled ? "disabled" : "enabled";
    label.value = enabled ? "Not Recording" : "Recording Clicks";
}

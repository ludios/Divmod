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

var IOSvc = Components.classes["@mozilla.org/network/io-service;1"]
                .getService( Components.interfaces.nsIIOService );

gPrefs = Components.classes["@mozilla.org/preferences-service;1"]
            .getService( Components.interfaces.nsIPrefService );
            
gPrefs = gPrefs.getBranch( "extensions.ClickChronicle." );
var recorderURL = gPrefs.getCharPref( "clickRecorderURL" );

function recordableURI( URI ) {
    return URI.schemeIs("http") && (URI.userPass == "");
    /* todo: compare URI against user-supplied filters,
       and common sense stuff like ignoring visits to clickchronicle */
}

function recordQuery( qstring ) {
    var req = new XMLHttpRequest();
    req.open( "GET", recorderURL + qstring, true ); 
    req.send( null );
}

function pageLoaded( event ) {
    var document = event.originalTarget;
    var URI = document.location;
    if(recordableURI(IOsvc.newURI( URI, null, null ))) {
        var qstring = "?url=" + URI;
        if( 0 < document.title.length )
            qstring = qstring + "&title=" + document.title;
        recordQuery( qstring );
    }
}

function toggleRecording() {
   gBrowser.addEventListener( "load", pageLoaded, true );
}

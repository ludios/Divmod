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
    - page information:
        the server originally included a facility for the client to send
        the page title along with the URL, i don't think this is realistic
        as long as we're using the observer service to track hits because
        as far as i know, we don't have access to the document attributes,
        and they're pretty meaningless as the extension currently works 
        across tabs and suchlike
    stuff to add, maybe:
    - make the recording toggle operate per-tab, so indiscretions can be
      perpetrated in a designated area
*/

function recordableURI( URI ) {
    return URI.schemeIs("http") && (URI.userPass == "");
    /* todo: compare URI against user-supplied filters,
       and common sense stuff like ignoring visits to clickchronicle */
}

function recordResponse( channel ) {
    var URI = channel.URI.QueryInterface( Components.interfaces.nsIURI );
    if(recordableURI( URI ))
        alert( URI.spec );
}

function ResponseObserver() {}

ResponseObserver.prototype = {
    /* observer boilerplate */
    QueryInterface : function( iid ) {
        with( Components.interfaces )
            if(iid.equals( nsIObserver ) || iid.equals( nsISupports ))
                return this;
            else
                throw Components.results.NS_ERROR_NO_INTERFACE;
    },
    /* called upon receipt of http response headers */
    observe : function( subject, topic, data ) {
        var channel = subject.QueryInterface( Components.interfaces.nsIChannel );
        /* this test will be true if the page-load is the direct result of
           user interfaction, e.g. typed URL, link click, or HTTP redirect 
           arising from either of those - IOW it wont log stuff like iframes 
           or inline images */
        if( channel.loadFlags & channel.LOAD_INITIAL_DOCUMENT_URI )
            recordResponse( channel );
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

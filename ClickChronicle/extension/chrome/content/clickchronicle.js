var gIOSvc = Components.classes["@mozilla.org/network/io-service;1"]
                .getService(Components.interfaces.nsIIOService);

var gConsoleSvc = Components.classes['@mozilla.org/consoleservice;1']
                    .getService(Components.interfaces.nsIConsoleService);
                    
var gCCPrefs = Components.classes["@mozilla.org/preferences-service;1"]
                .getService(Components.interfaces.nsIPrefService)
                    .getBranch("extensions.ClickChronicle.");

function substitute() {
    var args = substitute.arguments;
    var str  = args[0];
    for( i = 1 ; i < args.length ; i++ )
        str = str.replace( /%s/, args[i] );
    return str;
}
        
function recordableURI( URI ) {
    /* optimize preference getting */
    var gRecorderURI = gIOSvc.newURI(gCCPrefs.getCharPref("clickRecorderURL"), null, null);
    return URI.schemeIs("http") && (URI.userPass == "") && (URI.host != gRecorderURI.host)
}

function logToServer(document) {
    gConsoleSvc.logStringMessage("recording: " + document.location.href + " " + document.title);
    var req = new XMLHttpRequest();
    var targetURL = gCCPrefs.getCharPref("clickRecorderURL");
    targetURL += substitute("?url=%s&title=%s&ref=%s",
                            encodeURIComponent(document.location.href),
                            encodeURIComponent(document.title),
                            encodeURIComponent(document.referrer));
                            
    req.open("POST", targetURL, true);
    req.send(null);
}

function domContentLoaded(tabBrowser, appContent, event) {
    var win = event.target.defaultView;
    if(win == win.top) {
        var URI = gIOSvc.newURI(win.location.href, null, null);
        if(recordableURI(URI)) 
            logToServer(win.document);
    }
}

function chromeLoaded(event) {
    var tabBrowser = document.getElementById("content");
    var appContent = document.getElementById("appcontent");
    function part(e) { domContentLoaded(tabBrowser, appContent, e) }
    appContent.addEventListener("DOMContentLoaded", part, false);
    window.removeEventListener("load", chromeLoaded, false);
}

window.addEventListener("load", chromeLoaded, false);

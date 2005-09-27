var gIOSvc = Components.classes["@mozilla.org/network/io-service;1"]
                .getService(Components.interfaces.nsIIOService);

var gConsoleSvc = Components.classes['@mozilla.org/consoleservice;1']
                    .getService(Components.interfaces.nsIConsoleService);
                    
function recordableURI(uri) { return true; }

function domContentLoaded(tabBrowser, appContent, event) {
    var win = event.target.defaultView;
    if(win == win.top) {
        var URI = gIOSvc.newURI(win.location.href, null, null);
        if(recordableURI(URI))
            gConsoleSvc.logStringMessage(win.location.href + " " + win.document.title);
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

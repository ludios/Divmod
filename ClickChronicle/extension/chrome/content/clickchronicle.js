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

function log(str) {
    gConsoleSvc.logStringMessage("clickchronicle : " + str);
}

function showToolbarButtons() {
    var buttons = ["clickchronicle-record-button", "clickchronicle-pause-button"];
    var navToolbar  = document.getElementById("nav-bar");
    var afterButton = document.getElementById("urlbar-container");

    for(var i = 0; i < buttons.length; i++ )
        if (navToolbar.currentSet.indexOf(buttons[i]) == -1)
                navToolbar.insertItem(buttons[i] , afterButton, null, false);
}

var gCCBrowserObserver = {
    recordButton : null,
    pauseButton  : null,
    appContent   : null,
    tabBrowser   : null,

    QueryInterface : function(iid) {
        if(iid.equals(Components.interfaces.nsIObserver)
            || iid.equals(Components.interfaces.nsISupports))
            return this;
        log("QueryInterface to unsupported iid: " + iid);
        throw Components.results.NS_NOINTERFACE;
    },

    recordableURI : function(URI) {
        /* optimize preference getting */
        var recorderURI = gIOSvc.newURI(gCCPrefs.getCharPref("clickRecorderURL"), null, null);
        return URI.schemeIs("http") && (URI.userPass == "") && (URI.host != recorderURI.host)
    },

    logToServer : function(document) {
        log("recording: " + document.location.href + " " + document.title);
        var req = new XMLHttpRequest();
        var targetURL = gCCPrefs.getCharPref("clickRecorderURL");
        
        targetURL += substitute("?url=%s&title=%s&ref=%s",
                                encodeURIComponent(document.location.href),
                                encodeURIComponent(document.title),
                                encodeURIComponent(document.referrer));
                            
        req.open("POST", targetURL, true);
        req.send(null);
    },
    
    chromeLoaded : function(event) {
        window.removeEventListener("load", this.chromeLoaded, false);
        showToolbarButtons();
        
        var urgh = gCCBrowserObserver;
        urgh.recordButton = document.getElementById("clickchronicle-record-button");
        urgh.pauseButton  = document.getElementById("clickchronicle-pause-button");
        urgh.appContent   = document.getElementById("appcontent");
        urgh.tabBrowser   = document.getElementById("content");

        if(gCCPrefs.getBoolPref("enableOnStartup"))
            urgh.startRecording();
    },
        
    domContentLoaded : function(event) {
        var win = event.target.defaultView;
        if(win == win.top) {
            var URI = gIOSvc.newURI(win.location.href, null, null);
            if(gCCBrowserObserver.recordableURI(URI)) 
                gCCBrowserObserver.logToServer(win.document);
        }
    },

    startRecording : function() {
        this.recordButton.hidden = true;
        this.pauseButton.hidden = false;
        login(gIOSvc.newURI(gCCPrefs.getCharPref("clickRecorderURL"), null, null), function(s){});
        this.appContent.addEventListener("DOMContentLoaded", this.domContentLoaded, false);
    },

    stopRecording : function() {
        this.recordButton.hidden = false;
        this.pauseButton.hidden  = true;
        this.appContent.removeEventListener("DOMContentLoaded", this.domContentLoaded, false);
    }
}
         
window.addEventListener("load", gCCBrowserObserver.chromeLoaded, false);

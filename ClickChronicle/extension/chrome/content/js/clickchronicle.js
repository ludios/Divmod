var gClickChronicleObs = {
    recordButton : null,
    busyButton   : null,
    pauseButton  : null,
    appContent   : null,
    tabBrowser   : null,

    IOService : Components.classes["@mozilla.org/network/io-service;1"]
                     .getService(Components.interfaces.nsIIOService),

    CCPrefs : Components.classes["@mozilla.org/preferences-service;1"]
                  .getService(Components.interfaces.nsIPrefService)
                      .getBranch("extensions.ClickChronicle."),

    ConsoleService : Components.classes["@mozilla.org/consoleservice;1"]
                            .getService(Components.interfaces.nsIConsoleService),

    QueryInterface : function(iid) {
        if(iid.equals(Components.interfaces.nsIObserver)
            || iid.equals(Components.interfaces.nsISupports))
            return gClickChronicleObs;
        throw Components.results.NS_NOINTERFACE;
    },

    printDebug : function(msg) {
        if(gClickChronicleObs.CCPrefs.getBoolPref("debug"))
            gClickChronicleObs.ConsoleService.logStringMessage("clickchronicle: " + msg);
    },

    showToolbarButtons : function() {
        var buttons = ["record", "busy", "pause"];

        var navToolbar  = document.getElementById("nav-bar");
        var afterButton = document.getElementById("urlbar-container");

        if(!(navToolbar && afterButton))
            return;

        for(var i = 0; i < buttons.length; i++) {
            var bname = "clickchronicle-" + buttons[i] + "-button";
            if (navToolbar.currentSet.indexOf(bname) == -1)
                    navToolbar.insertItem(bname , afterButton, null, false);
        }
    },

    substitute : function() {
        var str  = arguments[0];
        for(i = 1; i < arguments.length; i++)
            str = str.replace(/%s/, arguments[i].toString());
        return str;
    },

    recordableURI : function(URI) {
        var recorderURI = gClickChronicleObs.IOService.newURI(
            gClickChronicleObs.CCPrefs.getCharPref("clickRecorderURL"), null, null);

        return (URI.schemeIs("http") 
                    && (URI.userPass == "") 
                    && (URI.host != recorderURI.host))
    },

    logToServer : function(document) {
        var targetURL = gClickChronicleObs.CCPrefs.getCharPref("clickRecorderURL");

        targetURL += gClickChronicleObs.substitute("?url=%s&title=%s&ref=%s",
                                     encodeURIComponent(document.location.href),
                                     encodeURIComponent(document.title),
                                     encodeURIComponent(document.referrer));

        gClickChronicleObs.printDebug(
            gClickChronicleObs.substitute("logToServer(%s) - %s", 
                                          document, targetURL));

        try {
            var req = new XMLHttpRequest();
            req.open("POST", targetURL, true);
            req.send(null);
        } catch(e) {
            gClickChronicleObs.printDebug("caught exception " + e);
        }
    },

    chromeLoaded : function(event) {
        //if(!gClickChronicleObs.CCPrefs.getBoolPref("everLoaded")) {
        //    
        //    gClickChronicleObs.CCPrefs.setBoolPref("everLoaded", true);
        //}

        gClickChronicleObs.showToolbarButtons();

        gClickChronicleObs.printDebug(
            gClickChronicleObs.substitute(
                "entered chromeLoaded(%s)", event));

        function delayedLoad() {
            gClickChronicleObs.printDebug("entered delayedLoad()");
            window.removeEventListener("load", gClickChronicleObs.chromeLoaded, false);


            var recordButton = document.getElementById("clickchronicle-record-button");
            if(recordButton) {
                gClickChronicleObs.recordButton = recordButton;
                gClickChronicleObs.busyButton = document.getElementById("clickchronicle-busy-button");
                gClickChronicleObs.pauseButton = document.getElementById("clickchronicle-pause-button");
            }

            gClickChronicleObs.appContent = document.getElementById("appcontent");
            gClickChronicleObs.tabBrowser = document.getElementById("content");

            if(gClickChronicleObs.CCPrefs.getBoolPref("enableOnStartup")) {
                gClickChronicleObs.printDebug("enableOnStartup is true, starting to record");
                gClickChronicleObs.startRecording();
            } else
                gClickChronicleObs.printDebug("enableOnStartup is false, doing nothing");
        }
        setTimeout(delayedLoad, 2);
    },

    DOMContentLoaded : function(event) {
        gClickChronicleObs.printDebug(gClickChronicleObs.substitute("DOMContentLoaded(%s)", event));
        var win = event.target.defaultView;
        if(win == win.top) {
            var URI = gClickChronicleObs.IOService.newURI(win.location.href, null, null);
            if(gClickChronicleObs.recordableURI(URI))
                gClickChronicleObs.logToServer(win.document);
        }
    },

    startRecording : function() {
        gClickChronicleObs.printDebug("entered startRecording()");

        if(gClickChronicleObs.recordButton) {
            gClickChronicleObs.recordButton.hidden = true;
            gClickChronicleObs.busyButton.hidden = false;
        }

        function cbLoggedIn(result) {
            gClickChronicleObs.printDebug("entered cbLoggedIn(...)");

            var buttonsVisible = gClickChronicleObs.recordButton;

            if(buttonsVisible)
                gClickChronicleObs.busyButton.hidden = true;

            if(result) {
                if(buttonsVisible)
                    gClickChronicleObs.pauseButton.hidden = false;

                gClickChronicleObs.appContent.addEventListener(
                    "DOMContentLoaded", gClickChronicleObs.DOMContentLoaded, false);

            } else {
                gClickChronicleObs.stopRecording();

                if(buttonsVisible)
                    gClickChronicleObs.recordButton.hidden = false;
            }
        }

        var recorderURL = gClickChronicleObs.CCPrefs.getCharPref("clickRecorderURL");
        var recorderURI = gClickChronicleObs.IOService.newURI(recorderURL, null, null);

        gClickChronicleObs.printDebug(
            gClickChronicleObs.substitute(
                "calling gClickChronicleMantissaLogin.login(%s, ...)",
                recorderURL));

        gClickChronicleMantissaLogin.login(recorderURI, cbLoggedIn);
    },

    stopRecording : function() {
        gClickChronicleObs.recordButton.hidden = false;
        gClickChronicleObs.pauseButton.hidden  = true;
        gClickChronicleObs.appContent.removeEventListener("DOMContentLoaded", 
            gClickChronicleObs.DOMContentLoaded, false);
    }
}

window.addEventListener("load", gClickChronicleObs.chromeLoaded, false);

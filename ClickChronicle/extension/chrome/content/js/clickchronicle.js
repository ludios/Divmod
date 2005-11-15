var gClickChronicleObs = {
    state : null,

    button : null,
    appContent : null,
    tabBrowser : null,

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
        var navToolbar  = document.getElementById("nav-bar");
        var afterButton = document.getElementById("urlbar-container");
        navToolbar.insertItem("clickchronicle-button" , afterButton, null, false);
    },

    setBusyButtonState : function() {
        gClickChronicleObs.button.image = "chrome://clickchronicle/content/images/busy.png";
        gClickChronicleObs.button.disabled = true;
    },

    setUnpausedButtonState : function() {
        gClickChronicleObs.button.image = "chrome://clickchronicle/content/images/pause.png";
        gClickChronicleObs.button.disabled = false;
        gClickChronicleObs.button.onclick = new Function("ignore", "gClickChronicleObs.stopRecording(true)");
    },

    setPausedButtonState : function() {
        gClickChronicleObs.button.image = "chrome://clickchronicle/content/images/record.png";
        gClickChronicleObs.button.disabled = false;
        gClickChronicleObs.button.onclick = new Function("ignore", "gClickChronicleObs.startRecording(true)");
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

        try {
            var req = new XMLHttpRequest();
            req.open("POST", targetURL, true);
            req.send(null);
        } catch(e) {}
    },

    chromeLoaded : function(event) {
        var me = gClickChronicleObs;
        window.removeEventListener("load", me.chromeLoaded, false);
        me.showToolbarButtons();

        function delayedLoad() {
            me.button = document.getElementById("clickchronicle-button");
            me.appContent = document.getElementById("appcontent");
            me.tabBrowser = document.getElementById("content");

            function cbGotState(state) {
                if(state == "unpaused" || (state == null && 
                        me.CCPrefs.getBoolPref("enableOnStartup"))) {
                    me.startRecording(false);
                } else {
                    me.stopRecording(false);
                }
            }
            gClickChronicleStateChangeSentinel.pollStates(cbGotState);
        }
        setTimeout(delayedLoad, 2);
    },

    DOMContentLoaded : function(event) {
        var win = event.target.defaultView;
        if(win == win.top) {
            var URI = gClickChronicleObs.IOService.newURI(win.location.href, null, null);
            if(gClickChronicleObs.recordableURI(URI))
                gClickChronicleObs.logToServer(win.document);
        }
    },

    startRecording : function(notify) {
        var me = gClickChronicleObs;
        me.setBusyButtonState();

        function cbLoggedIn(result) {
            if(!result)
                return me.stopRecording(notify);

            me.state = "unpaused";
            me.setUnpausedButtonState();
            me.appContent.addEventListener("DOMContentLoaded", me.DOMContentLoaded, false);
            if(notify)
                gClickChronicleStateChangeSentinel.notify(
                    "clickchronicle-state-changed", "unpaused");
        }
        var recorderURL = me.CCPrefs.getCharPref("clickRecorderURL");
        var recorderURI = me.IOService.newURI(recorderURL, null, null);
        gClickChronicleMantissaLogin.login(recorderURI, cbLoggedIn);
    },

    stopRecording : function(notify) {
        gClickChronicleObs.state = "paused";
        if(notify)
            gClickChronicleStateChangeSentinel.notify(
                "clickchronicle-state-changed", "paused");
        gClickChronicleObs.setPausedButtonState();
        gClickChronicleObs.appContent.removeEventListener("DOMContentLoaded", 
            gClickChronicleObs.DOMContentLoaded, false);
    },

    quitting : function() {},

    stateChanged : function(newstate) {
        if(newstate == "paused")
            gClickChronicleObs.stopRecording(false);
        else
            gClickChronicleObs.startRecording(false);
    }
}

var gClickChronicleStateChangeSentinel = {

    magicId : Math.random().toString(),
    pollStateCallback : null,

    ObserverService : Components.classes["@mozilla.org/observer-service;1"]
                        .getService(Components.interfaces.nsIObserverService),

    QueryInterface : function(iid) {
        if(iid.equals(Components.interfaces.nsIObserver)
            || iid.equals(Components.interfaces.nsISupports))
            return gClickChronicleStateChangeSentinel;
        throw Components.results.NS_NOINTERFACE;
    },

    handleStateChanged : function(messageData) {
        dump("cc: handleStateChanged\n");
        if(messageData[0] != gClickChronicleStateChangeSentinel.magicId)
            gClickChronicleObs.stateChanged(messageData[1]);
    },

    handleStateQuery : function(messageData) {
        dump("cc: handleStateQuery\n");
        if(messageData[0] != gClickChronicleStateChangeSentinel.magicId)
            gClickChronicleStateChangeSentinel.notify(
                "clickchronicle-state-notification", 
                gClickChronicleStateChangeSentinel.getState());
    },

    handleStateNotification : function(messageData) {
        dump("cc: handleStateNotification\n");
        var gccscs = gClickChronicleStateChangeSentinel;

        if(messageData[0] != gccscs.magicId && gccscs.pollStateCallback) {
            gccscs.pollStateCallback(messageData[1]);
            gccscs.pollStateCallback = null;
        }
    },

    observe : function(subject, topic, data) {
        /* notify the gClickChronicleObs local to this module
           that some other version of itself changed recording
           state */

        var unpacked = data.split(/,/);
        var gccscs = gClickChronicleStateChangeSentinel;
        var f = null;

        switch(topic) {
            case "clickchronicle-state-changed":
                f = gccscs.handleStateChanged;
                break;
            case "clickchronicle-state-query":
                f = gccscs.handleStateQuery;
                break;
            case "clickchronicle-state-notification":
                f = gccscs.handleStateNotification;
                break;
            default:
                dump("gClickChronicleStateChangeSentinel.observe got "
                     + " topic: " + topic + "\n");
                return;
        }

        f(unpacked);
    },

    notify : function(topic, data) {
       gClickChronicleStateChangeSentinel.ObserverService.notifyObservers(
            null, topic,
            [gClickChronicleStateChangeSentinel.magicId, data]);
    },

    latch : function() {
        var topics = ["clickchronicle-state-changed",
                      "clickchronicle-state-query",
                      "clickchronicle-state-notification"];

        for(var i = 0; i < topics.length; i++)
            gClickChronicleStateChangeSentinel
                .ObserverService
                    .addObserver(
                        gClickChronicleStateChangeSentinel,
                        topics[i], false);
    },

    getState : function() {
        return gClickChronicleObs.state;
    },

    canQI : function(thing, _interface) {
        try {
            thing.QueryInterface(_interface)
        } catch(e) { return false }
        return true
    },

    observerCount : function(topic) {
        var oenum = gClickChronicleStateChangeSentinel
                        .ObserverService.enumerateObservers(topic);
        var count = 0;
        while(oenum.hasMoreElements())
            if(gClickChronicleStateChangeSentinel.canQI(oenum.getNext(),
                    Components.interfaces.nsIObserver))
                count++;

        return count
    },

    pollStates : function(cbfunc) {
        dump("cc: gClickChronicleStateChangeSentinel.pollStates(...)\n");

        var gccscs = gClickChronicleStateChangeSentinel;
        var topic = "clickchronicle-state-query";
        var observers = gccscs.observerCount(topic) - 1;

        dump("cc: ---> pollStates: got this many observers " + observers + "\n");

        if(0 < observers) {
            dump("cc: ---> pollStates: notifying observers\n");
            gccscs.pollStateCallback = cbfunc;
            gccscs.notify(topic, null);
        } else {
            dump("cc: ---> pollStates: calling back now with null\n");
            cbfunc(null);
        }
    }
}

var gClickChronicleQuitObserver = {
    isClickChronicle : true,

    ObserverService : Components.classes["@mozilla.org/observer-service;1"]
                        .getService(Components.interfaces.nsIObserverService),

    QueryInterface : function(iid) {
        if(iid.equals(Components.interfaces.nsIObserver)
            || iid.equals(Components.interfaces.nsISupports))
            return gClickChronicleQuitObserver;
        throw Components.results.NS_NOINTERFACE;
    },

    observe : function(subject, topic, data) {
        if(topic == "quit-application")
            gClickChronicleObs.quitting()
    },

    latch : function() {
        /* maybe i was loaded in another window, check to ensure no other
           observer claiming to be clickchronicle is registered for this topic */

        /* this code may not work - for some reason we cannot seem to access
         * non-standard attributes of the objects in the observers' enumerator,
         * even though we override QueryInterface to return ourself unmodified
         * for nsIObserver/nsISupports adaptation */

        var oenum = gClickChronicleQuitObserver.ObserverService.enumerateObservers("quit-application");

        while(oenum.hasMoreElements()) {
            var thing = oenum.getNext();
            if(thing) {
                try {
                    thing = thing.QueryInterface(Components.interfaces.nsIObserver)
                } catch(e) { continue }
                if(thing.isClickChronicle)
                    return;
            }
        }

        gClickChronicleQuitObserver.ObserverService.addObserver(
            gClickChronicleQuitObserver, "quit-application", false);
    }
}

/* get gClickChronicleQuitObserver to look for quit attempts */
gClickChronicleQuitObserver.latch();
/* get gClickChronicleStateChangeSentinel to look for state changes */
gClickChronicleStateChangeSentinel.latch();
/* this javascript file will get loaded each time a new window is opened,
   and then window loads, gClickChronicleObs.chromeLoaded will get called */
window.addEventListener("load", gClickChronicleObs.chromeLoaded, false);

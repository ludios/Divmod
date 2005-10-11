var gIOSvc = Components.classes["@mozilla.org/network/io-service;1"]
                .getService(Components.interfaces.nsIIOService);

var gConsoleSvc = Components.classes['@mozilla.org/consoleservice;1']
                    .getService(Components.interfaces.nsIConsoleService);

var gCCPrefs = Components.classes["@mozilla.org/preferences-service;1"]
                .getService(Components.interfaces.nsIPrefService)
                    .getBranch("extensions.ClickChronicle.");

function clickchronicle_mutableURI(URI) {
    this.URI = URI.clone();
    this.child = function(cname) {
        if(this.URI.spec[this.URI.spec.length-1] != "/")
            cname = "/" + cname;
        this.URI.spec += cname;
        return this;
    };
    this.prePath = function() {
        this.URI.spec = this.URI.prePath;
        return this;
    };
    this.toString = function() { return this.URI.spec };
}

var gClickChronicleUtils = {

    log : function(str) {
        gConsoleSvc.logStringMessage("clickchronicle : " + str);
    },

    responseCode : function(toURL, cbfunc) {
        var req = new XMLHttpRequest();
        req.onload  = function(event) { cbfunc(event.target.status) }
        req.onerror = function(event) { cbfunc(null) }
        req.open("GET", toURL, false);
        req.send(null);
    },

    getElementValue : function(e) {
        /* i find myself needing this function everywhere */
        if(e.tagName == "textbox")
            return e.value;
        if(e.tagName == "checkbox")
            return e.checked;
    }
}

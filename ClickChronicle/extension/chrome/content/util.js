var gIOSvc = Components.classes["@mozilla.org/network/io-service;1"]
                .getService(Components.interfaces.nsIIOService);

var gConsoleSvc = Components.classes['@mozilla.org/consoleservice;1']
                    .getService(Components.interfaces.nsIConsoleService);

var gCCPrefs = Components.classes["@mozilla.org/preferences-service;1"]
                .getService(Components.interfaces.nsIPrefService)
                    .getBranch("extensions.ClickChronicle.");

var gCookieManager2 = Components.classes["@mozilla.org/cookiemanager;1"]
                        .getService(Components.interfaces.nsICookieManager2);

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
        req.onload = req.onerror = function(event) {
            try { var status = event.target.status } catch(e) { cbfunc(null); return }
            cbfunc(status);
        }
        req.open("GET", toURL, true);
        req.send(null);
    },

    asyncFormPOST : function(toURL, formvars, cbfunc) {
        /* POST formvars ({"key" : "value", ...}) to toURL, calling back
        * cbfunc with the response's status code */
        var qargs = new Array();
        for(var i in formvars)
            qargs.push(i + "=" + encodeURIComponent(formvars[i].toString()));
        qargs = qargs.join("&");

        var req = new XMLHttpRequest();
        req.onload = req.onerror = function(event) {
            var status = null;
            try { status = event.target.status } catch(e) {cbfunc(false); return};
            cbfunc(status.toString()[0] <= 3);
        }

        req.open("POST", toURL, false);
        req.setRequestHeader("content-type", "application/x-www-form-urlencoded");
        req.send(qargs);
    },

    getElementValue : function(e) {
        /* i find myself needing this function everywhere */
        if(e.tagName == "textbox")
            return e.value;
        if(e.tagName == "checkbox")
            return e.checked;
    }
}

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
    makePrivateURI : function(URI) {
        return new clickchronicle_mutableURI(URI).prePath().child("private").URI;
    },
    asyncFormPOST : function(toURI, formvars, cbfunc) {
        /* POST formvars ({"key" : "value", ...}) to toURI, calling back
        * cbfunc with the response's status code */
        var qargs = new Array();
        for(var i in formvars)
            qargs.push(i + "=" + encodeURIComponent(formvars[i].toString()));
        qargs = qargs.join("&");

        var req = new XMLHttpRequest();
        /* here is where the shitness of nevow.guard[1] and XMLHTTPRequest[2] converge 
           [1] login successful?  301!  login failed?  302!!
           [2] response is only available as a Document object if the content-type = text/xml 

           the upshot of this is that we have no way to find out if we actually got logged in
           or not, without making a second http request */

        req.onerror = function(e) { cbfunc(false) };
        req.onload  = function(e) { clickchronicle_loggedIn(toURI, cbfunc) };
        req.open("POST", toURI.spec, false);
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

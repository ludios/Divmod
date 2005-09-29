var gIOSvc = Components.classes["@mozilla.org/network/io-service;1"]
                .getService(Components.interfaces.nsIIOService);

var gConsoleSvc = Components.classes['@mozilla.org/consoleservice;1']
                    .getService(Components.interfaces.nsIConsoleService);
                    
var gCCPrefs = Components.classes["@mozilla.org/preferences-service;1"]
                .getService(Components.interfaces.nsIPrefService)
                    .getBranch("extensions.ClickChronicle.");

function mutableURI(URI) {
    this.URI = URI.clone();
    this.child = function(cname) {
        this.URI.spec += "/" + cname;
        return this;
    };
}

function responseCode(toURL, cbfunc) {
    var req = new XMLHttpRequest();
    req.onload = req.onerror = function(event) {
        try { var status = event.target.status } catch(e) { cbfunc(null); return }
        cbfunc(status);
    }
    req.open("GET", toURL, true);
    req.send(null);
}
        
function asyncFormPOST(toURL, formvars, cbfunc) {
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

    req.open("POST", toURL, true);
    req.setRequestHeader("content-type", "application/x-www-form-urlencoded");
    req.send(qargs);
}

function getElementValue(e) {
    /* i find myself needing this function everywhere */
    if(e.tagName == "textbox")
        return e.value;
    if(e.tagName == "checkbox")
        return e.checked;
}


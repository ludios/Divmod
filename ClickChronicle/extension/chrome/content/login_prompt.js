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
        try { status = event.target.status } catch(e) {};
        cbfunc(status);
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

function onClickLogin() {
    /* collate values of elements with a "formelement" attribute, and POST
     * them to the URL our window was passed */
    var formelems = document.getElementsByAttribute("formelement", "true");
    var formvars = new Object();
    
    for(var i = 0; i < formelems.length; i++) {
        var e = formelems[i];
        formvars[e.getAttribute("name")] = getElementValue(e);
    }

    var mantissaURI = window.arguments[0];
    var cbfunc = window.arguments[1];
    var port = 80;
    if(mantissaURI.port)
        port = mantissaURI.port;
    var toURL = "http://" + mantissaURI.host + ":" + port + "/__login__";
    
    asyncFormPOST(toURL, formvars, cbfunc);
    window.close();
}

function clickchronicle_windowClosed() {
    window.arguments[1](false);
}

function onClickLogin() {
    window.onclose = null;
    /* collate values of elements with a "formelement" attribute, and POST
     * them to the URL our window was passed */
    var formelems = document.getElementsByAttribute("formelement", "true");
    var formvars = new Object();

    for(var i = 0; i < formelems.length; i++) {
        var e = formelems[i];
        formvars[e.getAttribute("name")] = gClickChronicleUtils.getElementValue(e);
    }

    var mantissaURI = window.arguments[0];
    var cbfunc = window.arguments[1];
    var port = 80;
    if(mantissaURI.port != -1)
        port = mantissaURI.port;
    var toURL = new clickchronicle_mutableURI(mantissaURI).prePath().child("__login__").toString();
    gClickChronicleUtils.asyncFormPOST(toURL, formvars, cbfunc);
    window.close();
}

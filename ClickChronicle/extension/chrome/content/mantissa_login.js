function clickchronicle_loginPrompt(mantissaURI, cbfunc) {
    window.openDialog("chrome://clickchronicle/content/login_prompt.xul", -1,
                      "chrome,centerscreen,resizable=no", mantissaURI, cbfunc);
}

function clickchronicle_loggedIn(mantissaURI, cbfunc) {
    var iter = gCookieManager2.enumerator;
    while(iter.hasMoreElements()) {
        var cookie = iter.getNext();

        try {
            cookie = cookie.QueryInterface(Components.interfaces.nsICookie2);
        } catch(e) { continue }
        if(cookie.rawHost == mantissaURI.host)
            if(cookie.isSession) {
                var URI = new clickchronicle_mutableURI(mantissaURI).child("private").URI;
                gClickChronicleUtils.responseCode(URI, function(status) {cbfunc(status != 404) });
                return;
            } else { cbfunc(true); return }
    }
    cbfunc(false);
}

function clickchronicle_login(mantissaURI, cbfunc) {
    function cbLoggedIn(result) {
        if(result)
            cbfunc(true);
        else
            clickchronicle_loginPrompt(mantissaURI, cbfunc);
    }
    clickchronicle_loggedIn(mantissaURI, cbLoggedIn);
}

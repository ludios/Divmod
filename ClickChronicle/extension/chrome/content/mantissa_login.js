var gCookieManager = Components.classes["@mozilla.org/cookiemanager;1"]
                        .getService(Components.interfaces.nsICookieManager2);

function loginPrompt(mantissaURI, cbfunc) {
    window.openDialog("chrome://clickchronicle/content/login_prompt.xul", -1,
                      "chrome,centerscreen,resizable=no", mantissaURI, cbfunc);
}

function loggedIn(mantissaURI, cbfunc) {
    var iter = gCookieManager.enumerator;
    while(iter.hasMoreElements()) {
        var cookie = iter.getNext();

        try {
            cookie = cookie.QueryInterface(Components.interfaces.nsICookie2);
        } catch(e) { continue }

        if(cookie.rawHost == mantissaURI.host)
            if(cookie.isSession) {
                var URI = new mutableURI(mantissaURI).child("private").URI;
                responseCode(URI, function(status) { cbfunc(status != 404) });
                return;
            } else {
                cbfunc(true); return;
            }
    }
    cbfunc(false);
}

function login(mantissaURI, cbfunc) {
    function cbLoggedIn(result) {
        if(result)
            cbfunc(true);
        else
            loginPrompt(mantissaURI, cbfunc);
    }

    loggedIn(mantissaURI, cbLoggedIn);
}

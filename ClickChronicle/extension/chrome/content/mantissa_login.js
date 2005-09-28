 var gCookieManager = Components.classes["@mozilla.org/cookiemanager;1"]
                        .getService(Components.interfaces.nsICookieManager);

function loggedIn(mantissaURI) {
    var iter = gCookieManager.enumerator;
    while(iter.hasMoreElements()) {
        var cookie = iter.getNext();
        if(cookie instanceof Components.interfaces.nsICookie && cookie.host == mantissaURI.host)
            return true;
    }
    return false;
}

function loginPrompt(mantissaURI, cbfunc) {
    window.openDialog("chrome://clickchronicle/content/login_prompt.xul", -1,
                      "chrome,centerscreen,resizable=no", mantissaURI, cbfunc);
}

function login(mantissaURI, cbfunc) {
    if(loggedIn(mantissaURI))
        cbfunc(true);
    else
        loginPrompt(mantissaURI, cbfunc);
}

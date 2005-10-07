function clickchronicle_loginPrompt(mantissaURI, cbfunc) {
    window.openDialog("chrome://clickchronicle/content/login_prompt.xul", -1,
                      "chrome,centerscreen,resizable=no", mantissaURI, cbfunc);
}

function clickchronicle_loggedIn(mantissaURI, cbfunc) {
    /* append "/private" to the URL we were given */
    var URI = new clickchronicle_mutableURI(mantissaURI).child("private").URI.spec;
    /* callback cbfunc with a boolean indicating whether the response code of
     * fetching "URI" wasn't null, and wasn't 404 */
    function cbResponseCode(status) {
        if(status && status != 404)
            cbfunc(true);
        else
            cbfunc(false);
    }
    gClickChronicleUtils.responseCode(URI, cbResponseCode);
}

function clickchronicle_login(mantissaURI, cbfunc) {
    /* wrap the callback function in another that will login
       to the mantissa server if we're not already */
    function cbLoggedIn(result) {
        if(result)
            cbfunc(true);
        else /* the callback will now fire with the result of
                the login attempt */
            clickchronicle_loginPrompt(mantissaURI, cbfunc);
    }
    clickchronicle_loggedIn(mantissaURI, cbLoggedIn);
}

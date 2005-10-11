function clickchronicle_loginPrompt(mantissaURI, cbfunc) {
    window.openDialog("chrome://clickchronicle/content/login_prompt.xul", -1,
                      "chrome,centerscreen,resizable=no", mantissaURI, cbfunc);
}

function clickchronicle_makePrivateURI(URI) {
    return new clickchronicle_mutableURI(URI).prePath().child("private").URI;
}

function clickchronicle_formPost(toURI, formvars, cbfunc) {
    /* POST formvars ({"key" : "value", ...}) to toURI, calling back
    * cbfunc with the response's status code */
    var qargs = new Array();
    for(var i in formvars)
        qargs.push(i + "=" + encodeURIComponent(formvars[i].toString()));
    qargs = qargs.join("&");

    var req = new XMLHttpRequest();
    /* here is where the shitness of nevow.guard[1] and XMLHTTPRequest[2] converge 
        [1] login successful?  REDIRECT!  login failed?  REDIRECT!!
        [2] response is only available as a Document object if the content-type = text/xml 

        the upshot of this is that we have no way to find out if we actually got logged in
        or not, without making a second http request */

    req.onerror = function(e) { cbfunc(false) };
    req.onload  = function(e) { clickchronicle_loggedIn(toURI.URI, cbfunc) };

    req.open("POST", toURI.toString(), false);
    req.setRequestHeader("content-type", "application/x-www-form-urlencoded");
    req.send(qargs);
}

function clickchronicle_loggedIn(mantissaURI, cbfunc) {
    /* append "/private" to the URL we were given */
    var URL = clickchronicle_makePrivateURI(mantissaURI).spec;

    /* callback cbfunc with a boolean indicating whether the response code of
     * fetching "URI" wasn't null, and wasn't 404 */
    function cbResponseCode(status) {
        if(status && status != 404)
            cbfunc(true);
        else
            cbfunc(false);
    }
    gClickChronicleUtils.responseCode(URL, cbResponseCode);
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

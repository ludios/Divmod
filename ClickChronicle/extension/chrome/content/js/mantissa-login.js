function ClickChronicleMutableURI(URI) {
    this.URI = URI.clone();
}

ClickChronicleMutableURI.prototype = {
    child  : function(cname) {
        if(this.URI.spec[this.URI.spec.length-1] != "/")
            cname = "/" + cname;
        this.URI.spec += cname;
        return this;
    },

    prePath : function() {
        this.URI.spec = this.URI.prePath;
        return this;
    },

    top : function(segment) {
        return this.prePath().child(segment);
    },

    toString : function() { return this.URI.spec }
}

var gClickChronicleMantissaLogin = {
    mantissaURI : null,
    privateURI  : null,
    loginURI    : null,

    CCPrefs : Components.classes["@mozilla.org/preferences-service;1"]
                  .getService(Components.interfaces.nsIPrefService)
                      .getBranch("extensions.ClickChronicle."),

    ConsoleService : Components.classes["@mozilla.org/consoleservice;1"]
                            .getService(Components.interfaces.nsIConsoleService),

    printDebug : function(msg) {
        if(gClickChronicleMantissaLogin.CCPrefs.getBoolPref("debug"))
            gClickChronicleMantissaLogin.ConsoleService
                .logStringMessage("clickchronicle: " + msg);
    },

    substitute : function() {
        var str  = arguments[0];
        for(i = 1; i < arguments.length; i++)
            str = str.replace(/%s/, arguments[i].toString());
        return str;
    },

    onClickLogin : function(cbfunc, formelems) {
        gClickChronicleMantissaLogin.printDebug("onClickLogin()");
        /* collate values of elements with a "formelement" attribute, and POST
         * them to the URL our window was passed */

        var formvars = new Object();

        for(var i = 0; i < formelems.length; i++) {
            var e = formelems[i];
            formvars[e.getAttribute("name")] = gClickChronicleMantissaLogin.getElementValue(e);
        }

        /* window.arguments[1] is a callback function */
        gClickChronicleMantissaLogin.formPost(formvars, cbfunc);
    },

    getElementValue : function(e) {
        if(e.tagName == "textbox")
            return e.value;
        if(e.tagName == "checkbox")
            return e.checked;
    },

    loginPrompt : function(cbfunc) {
        gClickChronicleMantissaLogin.printDebug("loginPrompt(...)");
        /* pass ourself to the login window, and a callback function */

        function cbClickedLogin(result) {
            if(result)
                gClickChronicleMantissaLogin.onClickLogin(cbfunc, result);
            else
                cbfunc(result);
        }

        window.openDialog("chrome://clickchronicle/content/xul/login-prompt.xul", -1,
                          "chrome,centerscreen,resizable=no", 
                          cbClickedLogin)
    },

    responseCode : function(cbfunc) {
        function msg(m) { gClickChronicleMantissaLogin.printDebug(m) }
        msg("responseCode being called with " + gClickChronicleMantissaLogin.privateURI.spec);

        try {
            var req = new XMLHttpRequest();
            req.onload  = function(event) {
                msg("onload handler called in responseCode");
                msg("THE STATUS IS " + event.target.status);
                cbfunc(event.target.status)
            }
            req.onerror = function(event) {
                msg("onerror handler called in responseCode");
                cbfunc(null)
            }
            req.open("GET", gClickChronicleMantissaLogin.privateURI.spec, false);
            req.send(null)
        } catch(e) {
            msg("exception raised in responseCode");
            cbfunc(null)
        }
    },

    formPost : function(formvars, cbfunc) {
        try {
            var qargs = new Array();
            for(var i in formvars)
                qargs.push(i + "=" + encodeURIComponent(formvars[i].toString()));
            qargs = qargs.join("&");

            var req = new XMLHttpRequest();
        } catch(e) { cbfunc(null); return }

        req.onerror = function(e) { cbfunc(false) }
        req.onload  = function(e) {
            gClickChronicleMantissaLogin.loggedIn(cbfunc)
        }

        try {
            req.open("POST", gClickChronicleMantissaLogin.loginURI.spec, false);
            req.setRequestHeader("content-type", "application/x-www-form-urlencoded");
            req.send(qargs);
        } catch(e) { cbfunc(null) }
    },

    loggedIn : function(cbfunc) {
        gClickChronicleMantissaLogin.printDebug("loggedIn(...)");
        /* append "/private" to the URL we were given */
        /* callback cbfunc with a boolean indicating whether the response code of
        * fetching "URI" wasn't null, and wasn't 404 */
        function cbResponseCode(status) {
            gClickChronicleMantissaLogin.printDebug("cbResponseCode");

            if(status && status != 404)
                cbfunc(true);
            else if(status == null)
                cbfunc(null);
            else
                cbfunc(false);
        }
        gClickChronicleMantissaLogin.printDebug("calling responseCode(...)");
        gClickChronicleMantissaLogin.responseCode(cbResponseCode);
    },

    login : function(mantissaURI, cbfunc) {
        gClickChronicleMantissaLogin.printDebug(
            gClickChronicleMantissaLogin.substitute("login(%s, ...)", mantissaURI));

        gClickChronicleMantissaLogin.mantissaURI = mantissaURI;

        function mktop(segment) {
            return new ClickChronicleMutableURI(mantissaURI).top(segment).URI;
        }

        gClickChronicleMantissaLogin.privateURI = mktop("private");
        gClickChronicleMantissaLogin.loginURI   = mktop("__login__");

        /* wrap the callback function in another that will login
         to the mantissa server if we're not already */

        function cbLoggedIn(result) {
            gClickChronicleMantissaLogin.printDebug("cbLoggedIn(...)");

            if(result)
                cbfunc(true);
            else if(result == null) {
                alert("There was a problem communicating with " + mantissaURI.host);
                cbfunc(null);
            } else
                gClickChronicleMantissaLogin.loginPrompt(cbfunc);
        }
        gClickChronicleMantissaLogin.loggedIn(cbLoggedIn);
    }
}

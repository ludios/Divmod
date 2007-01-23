var gClickChronicleLoginPrompt = {

    windowargs : null,

    onLoadWindow : function() {
        gClickChronicleLoginPrompt.windowargs = window.arguments[0];
        document.getElementById("hostname").value = "(" + gClickChronicleLoginPrompt.windowargs["display-url"] + ")";
        document.getElementById("username").focus();
    },

    onCloseWindow : function() {
        gClickChronicleLoginPrompt.windowargs["callback"](null);
    },

    onClickLogin : function() {
        function getElementValue(e) {
            if(e.tagName == "textbox")
                return e.value;
            if(e.tagName == "checkbox")
                return e.checked;
        };

        var formelems = document.getElementsByAttribute("formelement", "true");
        var qargs = new Array();

        var felem = null;
        var value = null;

        for(var i = 0; i < formelems.length; i++) {
            felem = formelems[i];
            value = getElementValue(felem).toString();
            qargs.push(felem.getAttribute("name") + "=" + encodeURIComponent(value));
            felem.disabled = true;
        };

        qargs = qargs.join("&");

        var req = new XMLHttpRequest();

        var callback = gClickChronicleLoginPrompt.windowargs["callback"];

        req.onerror = function(e) { setTimeout(window.close, 10); callback(false) }
        req.onload  = function(e) { setTimeout(window.close, 10); callback(true) }

        req.open("POST", gClickChronicleLoginPrompt.windowargs["post-url"], true);
        req.setRequestHeader("content-type", "application/x-www-form-urlencoded");
        req.send(qargs);
    }
}

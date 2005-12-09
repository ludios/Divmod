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
        };

        qargs = qargs.join("&");

        var req = new XMLHttpRequest();
        req.onerror = function(e) {}
        req.onload  = function(e) {}

        req.open("POST", gClickChronicleLoginPrompt.windowargs["post-url"], true);
        req.setRequestHeader("content-type", "application/x-www-form-urlencoded");
        req.send(qargs);
    }
}

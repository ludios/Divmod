var gClickChronicleLoginPrompt = {

    onLoadWindow : function() {
        document.getElementById("hostname").value = "(" + window.arguments[1] + ")";
        document.getElementById("username").focus();
    },

    onCloseWindow : function() {
        var cbfunc = window.arguments[0];
        cbfunc(null);
    },

    onClickLogin : function() {
        var cbfunc = window.arguments[0];
        var formelems = document.getElementsByAttribute("formelement", "true");
        cbfunc(formelems);
        window.onclose = null;
        window.close();
    }
}

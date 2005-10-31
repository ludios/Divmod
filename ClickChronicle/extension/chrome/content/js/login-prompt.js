var gClickChronicleLoginPrompt = {

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

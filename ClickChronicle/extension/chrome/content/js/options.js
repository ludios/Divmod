const gClickChronicleStringPrefs = ["clickRecorderURL"];
const gClickChronicleBoolPrefs   = ["enableOnStartup"];

function clickchronicle_loadPrefs() {
    var prefs = Components.classes["@mozilla.org/preferences-service;1"]
                    .getService(Components.interfaces.nsIPrefService)
                        .getBranch("extensions.ClickChronicle.");

    for(var i in gClickChronicleStringPrefs) {
        var pref = gClickChronicleStringPrefs[i];
        document.getElementById(pref).value = prefs.getCharPref(pref);
    }

    for(i in gClickChronicleBoolPrefs) {
        pref = gClickChronicleBoolPrefs[i];
        document.getElementById(pref).checked = prefs.getBoolPref(pref);
    }
}

function clickchronicle_savePrefs() {
    var prefs = Components.classes["@mozilla.org/preferences-service;1"]
                    .getService(Components.interfaces.nsIPrefService)
                        .getBranch("extensions.ClickChronicle.");

    for(var i in gClickChronicleStringPrefs) {
        var pref = gClickChronicleStringPrefs[i];
        prefs.setCharPref(pref, document.getElementById(pref).value);
    }

    for(i in gClickChronicleBoolPrefs) {
        pref = gClickChronicleBoolPrefs[i];
        prefs.setBoolPref(pref, document.getElementById(pref).checked);
    }
}

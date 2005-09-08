var gPrefs = null;
const stringPrefs = ["clickRecorderURL"];
const boolPrefs = ["enableOnStartup"];

function loadPrefs() {
    gPrefs = Components.classes["@mozilla.org/preferences-service;1"]
                .getService(Components.interfaces.nsIPrefService);
    gPrefs = gPrefs.getBranch("extensions.ClickChronicle.");

    for( var i in stringPrefs )
        document.getElementById(stringPrefs[i]).value = gPrefs.getCharPref(stringPrefs[i]);

    for( i in boolPrefs )
        document.getElementById(boolPrefs[i]).checked = gPrefs.getBoolPref(boolPrefs[i]);
}

function savePrefs() {
    for( var i in stringPrefs )
        gPrefs.setCharPref(stringPrefs[i], document.getElementById(stringPrefs[i]).value);

    for( i in boolPrefs )
        gPrefs.setBoolPref(boolPrefs[i], document.getElementById(boolPrefs[i]).checked);
} 


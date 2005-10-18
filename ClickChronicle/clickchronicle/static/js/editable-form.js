function sanitizeBooleanOptions() {
    var bools = getElementsByTagAndClassName("span", "boolean-option");
    for(var i = 0; i < bools.length; i++) {
        var elemt = bools[i]
        var value = stripWS(elemt.firstChild.nodeValue);
        if(value == "1") value = "Yes";
        else if(value == "0") value = "No";
        else continue;
        elemt.firstChild.nodeValue = value;
    }
}

addLoadEvent(sanitizeBooleanOptions);

function edit(fieldname) {
    hideElement(fieldname + "Label");
    showElement(fieldname + "Controller");
    hideElement(fieldname + "Edit");
    showElement(fieldname + "Save");
}

function stripWS(text) {
    return text.replace(/^\s+/, "").replace(/\s+$/, "");
}

function edit_shareClicks() {
    var controller = $("shareClicksController");
    var radios = getElementsByTagAndClassName("input", null, controller);
    var elabel = stripWS($("shareClicksLabel").firstChild.nodeValue);
    for(var i = 0; i < radios.length; i++ ) {
        var radio = radios[i];
        if(stripWS(radio.nextSibling.nodeValue) == elabel)
            radio.checked = true;
        else
            radio.checked = false;
    }
    edit("shareClicks");
}

function save(fieldname) {
    var e = $(fieldname + "Controller");
    server.handle("save_" + fieldname, e.value);
    hideElement(e);
    showElement(fieldname + "Label");
    hideElement(fieldname + "Save");
    showElement(fieldname + "Edit");
}

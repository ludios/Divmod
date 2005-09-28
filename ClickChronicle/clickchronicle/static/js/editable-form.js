function edit(fieldname) {
    hideElement(fieldname + "Label");
    showElement(fieldname + "Controller");
    hideElement(fieldname + "Edit");
    showElement(fieldname + "Save")
}

function save(fieldname) {
    hideElement(fieldname + "Controller");
    showElement(fieldname + "Label");
    hideElement(fieldname + "Save");
    showElement(fieldname + "Edit") 
}
    

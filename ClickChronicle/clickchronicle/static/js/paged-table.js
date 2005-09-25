var activeSortCol = null;

function selectOptionWithValue( elem, value ) {
    for( var i = 0; i < elem.childNodes.length; i++ )
        if( elem.childNodes[i].value == value ) {
            elem.selectedIndex = i;
            break;
        }
}

ignore = partial(server.handle, "ignore");
bookmark = partial(server.handle, "bookmark");

function visible(e) {
    return e.style.display != "none";
}

var UP_ARROW = "\u2191";
var DN_ARROW = "\u2193";

function toggleSort(column) {
    var col = $("sortcol_" + column);
    if(col == activeSortCol) {
        var newDirection = ($("sortArrow").firstChild.nodeValue == UP_ARROW) ? "descending" : "ascending";
        server.handle("updateTable", getSelected("pages"), column, newDirection);
    } else
        server.handle("updateTable", getSelected("pages"), column);
}
    
function setSortState(column, direction) {
    try{ activeSortCol.removeChild($("sortArrow")) } catch(e) {}
    var col = $("sortcol_" + column);
    activeSortCol = col;
    var arrow = (direction == "ascending") ? UP_ARROW : DN_ARROW;
    col.appendChild(SPAN({"id":"sortArrow"}, arrow));
}

function doDisable(eid1, eid2) {
    var e1 = $(eid1), e2 = $(eid2);
    if(visible(e1) && visible(e2)) {
        hideElement(e1);
        hideElement(e2);
        setDisplayForElement(eid1 + "_disabled", "inline");
        setDisplayForElement(eid2 + "_disabled", "inline");
    }
}

function doEnable(eid1, eid2) {
    var e1 = $(eid1), e2 = $(eid2);
    if(!visible(e1) && !visible(e2)) {
        hideElement(eid1 + "_disabled");
        hideElement(eid2 + "_disabled");
        setDisplayForElement(e1, "inline");
        setDisplayForElement(e2, "inline");
    }
}
 
function firstPrevDisable() { doDisable("first", "prev") }
function firstPrevEnable() { doEnable("first", "prev") }
function lastNextDisable() { doDisable("last", "next") }
function lastNextEnable() { doEnable("last", "next") }

function setPageState() {
    var pages = $("pages");
    var onFirstPage = (pages.selectedIndex < 1);
    var onLastPage = (pages.selectedIndex == pages.childNodes.length - 1);
    (onFirstPage ? firstPrevDisable : firstPrevEnable)();
    (onLastPage  ? lastNextDisable  : lastNextEnable)()
    
    pages.disabled = (onFirstPage && onLastPage) ? true : false;
    var noItems = ($("totalItems").firstChild.nodeValue == 0);

    if(noItems) {
        hideElement("tableContainer");
        showElement("noClicksDialog");
        hideElement("positionDescription");
    } else {
        hideElement("noClicksDialog");
        showElement("tableContainer");
        setDisplayForElement("positionDescription", "table-cell");
    }
}

function setCurrentPage( page ) {
    selectOptionWithValue($("pages"), page);
    setPageState();
}

function setTotalItems( items ) {
    document.getElementById("totalItems").firstChild.nodeValue = items;
    setPageState();
}

function getSelected( selectId ) {
    var elem = $(selectId);
    return elem.childNodes[elem.selectedIndex].firstChild.nodeValue;
}

function updateTable() {
    server.handle("updateTable", getSelected("pages"));
}

function first() {
    var firstPageElem = document.getElementById("pages").firstChild;
    var firstPage = firstPageElem.firstChild.nodeValue;
    setCurrentPage( firstPage );
    updateTable();
}

function last() {
    var pagesElem = document.getElementById("pages");
    var lastPageElem = pagesElem.childNodes[pagesElem.childNodes.length - 1];
    var lastPage = lastPageElem.firstChild.nodeValue;
    setCurrentPage( lastPage );
    updateTable();
}
           
function next() {
    var pagesElem = document.getElementById("pages");
    var nextPageElem = pagesElem.childNodes[pagesElem.selectedIndex + 1];
    var nextPage = nextPageElem.firstChild.nodeValue;
    setCurrentPage( nextPage );
    updateTable();
}

function prev() {
    var pagesElem = document.getElementById("pages");
    var prevPageElem = pagesElem.childNodes[pagesElem.selectedIndex - 1];
    var prevPage = prevPageElem.firstChild.nodeValue;
    setCurrentPage( prevPage );
    updateTable();
}

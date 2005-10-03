/* map shorthand action names to names of handler functions
 * wrap them anonymously because they're not defined yet */

const actions = {
    "ignore"   : "doIgnore",
    "info"     : "doInfo",
    "bookmark" : "doBookmark",
    "delete"   : "doDelete"
};

function sub() {
    var args = sub.arguments;
    var str  = args[0];
    for(i = 1 ; i < args.length ; i++)
        str = str.replace(/%s/, args[i].toString());
    return str;
}

function cementActionLinks() {
    var clickTable = $("clickTable");
    var rows = getElementsByTagAndClassName("tr", null, clickTable);
    for(var i = 0; i < rows.length; i++) {
        var row = rows[i];
        if(!row.getAttribute("id"))
            continue;
        for(var aname in actions) {
            var links = getElementsByTagAndClassName("a", aname + "-action", row);
            for(var k = 0; k < links.length; k++) {
                var link = links[k];
                link.href = "#" + row.id; // so something shows in the statusbar
                link.onclick = new Function("ignore", sub("%s(%s); return false;", actions[aname], row.id));
            }
        }
    }
}

var activeSortCol = null;

function selectOptionWithValue( elem, value ) {
    for( var i = 0; i < elem.childNodes.length; i++ )
        if( elem.childNodes[i].value == value ) {
            elem.selectedIndex = i;
            break;
        }
}

function doIgnore(identifier) {
    server.handle("ignore", identifier);
}

function doBookmark(identifier) {
    server.handle("bookmark", identifier);
}

function doDelete(identifier) {
    server.handle("delete", identifier);
}

function closeInfo(identifier) {
    var tr = $(identifier).nextSibling;
    var cell = getElementsByTagAndClassName("td", "content", tr)[0];
    hideElement(tr);
    replaceChildNodes(cell);
}

function gotInfo(identifier, html) {
    var tr = $(identifier).nextSibling;
    var cell = getElementsByTagAndClassName("td", "content", tr)[0];
    cell.innerHTML = html;
    var close = getElementsByTagAndClassName("a", "close-info-action", tr)[0];
    close.onclick = function(e) { closeInfo(identifier); return false };
    setDisplayForElement("table-row", tr);
}

function doInfo(identifier) {
    server.handle("info", identifier);
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
    hideElement(e1);
    hideElement(e2);
    setDisplayForElement("inline", eid1 + "_disabled");
    setDisplayForElement("inline", eid2 + "_disabled");
}

function doEnable(eid1, eid2) {
    var e1 = $(eid1), e2 = $(eid2);
    setDisplayForElement("inline", e1);
    setDisplayForElement("inline", e2);
    hideElement(eid1 + "_disabled");
    hideElement(eid2 + "_disabled");
}

function firstPrevDisable() { doDisable("first", "prev") }
function lastNextDisable()  { doDisable("last", "next")  }
function firstPrevEnable()  { doEnable("first", "prev")  }
function lastNextEnable()   { doEnable("last", "next")   }

function setPageState() {
    var pages = $("pages");
    var onFirstPage = (pages.selectedIndex < 1);
    var onLastPage = (pages.selectedIndex == pages.childNodes.length - 1);

    (onFirstPage ? firstPrevDisable : firstPrevEnable)();
    (onLastPage  ? lastNextDisable  : lastNextEnable)();

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
}

function setTotalItems( items ) {
    document.getElementById("totalItems").firstChild.nodeValue = items;
    setPageState();
    cementActionLinks();
}

function getSelected( selectId ) {
    var elem = $(selectId);
    return elem.childNodes[elem.selectedIndex].firstChild.nodeValue;
}

function updateTable() {
    server.handle("updateTable", getSelected("pages"));
}

function goFirst() {
    var firstPageElem = document.getElementById("pages").firstChild;
    var firstPage = firstPageElem.firstChild.nodeValue;
    setCurrentPage( firstPage );
    updateTable();
}

function goLast() {
    var pagesElem = document.getElementById("pages");
    var lastPageElem = pagesElem.childNodes[pagesElem.childNodes.length - 1];
    var lastPage = lastPageElem.firstChild.nodeValue;
    setCurrentPage( lastPage );
    updateTable();
}

function goNext() {
    var pagesElem = document.getElementById("pages");
    var nextPageElem = pagesElem.childNodes[pagesElem.selectedIndex + 1];
    var nextPage = nextPageElem.firstChild.nodeValue;
    setCurrentPage( nextPage );
    updateTable();
}

function goPrev() {
    var pagesElem = document.getElementById("pages");
    var prevPageElem = pagesElem.childNodes[pagesElem.selectedIndex - 1];
    var prevPage = prevPageElem.firstChild.nodeValue;
    setCurrentPage( prevPage );
    updateTable();
}

/* map shorthand action names to names of handler functions
 * wrap them anonymously because they're not defined yet */

const actions = {
    "block"   : "doBlock",
    "info"     : "doInfo",
    "bookmark" : "doBookmark",
    "delete"   : "doDelete"
};

const tooltips = {
    "block" : "Block current and future clicks to this click's domain",
    "info" : "View click information",
    "bookmark" : "Bookmark click",
    "delete" : "Delete click"
}

/* if %s appears in the completion message, it will be replaced with the URL
 *  of the acted-upon click, or whatever identifier the server handler returns */

const completionMessages = {
    "block" : "Blocked '%s'",
    "bookmark" : 'Bookmarked "%s"',
    "delete" : "Deleted '%s'"
}

/* alternateRowClasses will cyclically assign these class names to rows in the
 * given table */

const alternate = ["fancyRowAlt", "fancyRow"];

function alternateRowClasses(table, withClass) {
    var rows = getElementsByTagAndClassName("tr", withClass, table);
    var numVisible = 0;
    for(var i = 0; i < rows.length; i++) {
        var row = rows[i];
        row.className = alternate[numVisible % alternate.length];
        numVisible += 1;
    }
}

function sub() {
    var args = sub.arguments;
    var str  = args[0];
    if(str.match(/%s/))
        for(i = 1 ; i < args.length ; i++)
            str = str.replace(/%s/, args[i].toString());
    return str;
}

function getActionLinks(action, parent) {
    return getElementsByTagAndClassName("a", sub("%s-action", action), parent);
}

function makeActor(action, identifier) {
    return new Function("block", sub("%s(%s); return false;", actions[action], identifier));
}

function makeTooltip(text) {
    return new Function("event", sub('toolTip("%s", this)', text));
}

function cementActionLinks() {
    var clickTable = $("clickTable");
    var rows = getElementsByTagAndClassName("tr", null, clickTable);
    for(var i = 0; i < rows.length; i++) {
        var row = rows[i];
        if(!row.getAttribute("id"))
            continue;
        for(var aname in actions) {
            var links = getActionLinks(aname, row);
            for(var j = 0; j < links.length; j++) {
                var link = links[j];
                link.href = "#" + row.id; // so something shows in the statusbar
                link.onclick = makeActor(aname, row.id);
                var img = getElementsByTagAndClassName("img", "linkIcon", link)[0];
                img.onmouseover = makeTooltip(link.getAttribute("alt"));
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

function doBlock(identifier) {
    server.handle("block", identifier);
}

function displayCompletionForAction(action, identifier) {
    var dialog = $("completionDialog");
    replaceChildNodes(dialog)
    dialog.appendChild(SPAN(null, sub(completionMessages[action], identifier)));
    new Fadomatic(dialog, 2).fadeOut();
}

bookmarked = partial(displayCompletionForAction, "bookmark");
deleted = partial(displayCompletionForAction, "delete");
blocked = partial(displayCompletionForAction, "block");

function doBookmark(identifier) {
    server.handle("bookmark", identifier);
}

function doDelete(identifier) {
    server.handle("delete", identifier);
}

function closeInfo(infoRow) {
    var cell = getElementsByTagAndClassName("td", "content", infoRow)[0];
    hideElement(infoRow);
    replaceChildNodes(cell);
}

function gotInfo(identifier, html) {
    var clickRow = $(identifier);
    var infoRow  = clickRow.nextSibling;
    var cell = getElementsByTagAndClassName("td", "content", infoRow)[0];
    cell.innerHTML = html;
    var infoLink = getActionLinks("info", clickRow)[0];
    infoLink.onclick = function(e) {
        closeInfo(infoRow);
        infoLink.onclick = makeActor("info", identifier);
        return false;
    }
    setDisplayForElement("table-row", infoRow);
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
        setDisplayForElement("table-cell", "positionDescription");
    }
}

function setCurrentPage( page ) {
    selectOptionWithValue($("pages"), page);
}

function setTotalItems( items ) {
    document.getElementById("totalItems").firstChild.nodeValue = items;
    setPageState();
    cementActionLinks();
    alternateRowClasses("clickTable", "clickTableRow");
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

function toolTip(text,me) {
  theObj=me;
  theObj.onmousemove=updatePos;
  document.getElementById('toolTipBox').innerHTML=text;
  document.getElementById('toolTipBox').style.display="block";
  window.onscroll=updatePos;
}

function updatePos() {
  var ev=arguments[0]?arguments[0]:event;
  var x=ev.clientX;
  var y=ev.clientY;
  diffX=24;
  diffY=0;
  document.getElementById('toolTipBox').style.top  = y-2+diffY+document.body.scrollTop+ "px";
  document.getElementById('toolTipBox').style.left = x-2+diffX+document.body.scrollLeft+"px";
  theObj.onmouseout=hideMe;
}

function hideMe() {
  document.getElementById('toolTipBox').style.display="none";
}


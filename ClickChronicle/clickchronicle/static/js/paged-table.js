function selectOptionWithValue( elem, value ) {
    for( var i = 0; i < elem.childNodes.length; i++ )
        if( elem.childNodes[i].value == value ) {
            elem.selectedIndex = i;
            break;
        }
}

function changedItemsPerPage() {
    server.handle("changeItemsPerPage", getSelected("pages"), getSelected("itemsPerPage"));
}

function setPageState() {
    /* this image disabling code is a mess */
    var pageElem = document.getElementById("pages");
    var onFirstPage = (pageElem.selectedIndex < 1);

    var first_e = document.getElementById("first_enabled");
    var prev_e  = document.getElementById("prev_enabled");

    first_e.style.display = prev_e.style.display = onFirstPage ? "none" : "inline";

    var first_d = document.getElementById("first_disabled");
    var prev_d  = document.getElementById("prev_disabled");

    first_d.style.display = prev_d.style.display = onFirstPage ? "inline" : "none";

    var onLastPage = (pageElem.selectedIndex == pageElem.childNodes.length - 1);
    
    var last_e = document.getElementById("last_enabled");
    var next_e = document.getElementById("next_enabled");

    last_e.style.display = next_e.style.display = onLastPage ? "none" : "inline";

    var last_d = document.getElementById("last_disabled");
    var next_d = document.getElementById("next_disabled");

    last_d.style.display = next_d.style.display = onLastPage ? "inline" : "none";

    pageElem.disabled = (onFirstPage && onLastPage) ? true : false;
    var noItems = (document.getElementById("totalItems").firstChild.nodeValue == 0);
    document.getElementById("itemsPerPage").enabled = noItems ? 'false' : 'true';
    var linkTable = document.getElementById("tableContainer");
    linkTable.style.display = noItems ? "none" : "block";
    var noClicksDialog = document.getElementById("noClicksDialog");
    noClicksDialog.style.display = noItems ? "block" : "none";
    var posDesc = document.getElementById("positionDescription");
    posDesc.style.display = noItems ? "none" : "table-cell";
}

function setCurrentPage( page ) {
    selectOptionWithValue(document.getElementById("pages"), page);
    setPageState();
}

function setTotalItems( items ) {
    alert("called with" + items);
    document.getElementById("totalItems").firstChild.nodeValue = items;
    setPageState();
}

function setItemsPerPage( items ) { 
    selectOptionWithValue(document.getElementById("itemsPerPage"), items);
}

function getSelected( selectId ) {
    /* because i dont think selectedItem is standard */
    var elem = document.getElementById( selectId );
    return elem.childNodes[elem.selectedIndex].firstChild.nodeValue;
}

function updateTable() {
    server.handle("updateTable", getSelected("pages"), getSelected("itemsPerPage"));
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

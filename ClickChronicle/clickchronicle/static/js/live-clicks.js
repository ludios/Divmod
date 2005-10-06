var clickchronicle_clickCount = 0;
var clickchronicle_clickLimit = 10;
function clickchronicle_addClick(title, url) {
    var clicks = document.getElementById('click-list');
    clickchronicle_clickCount += 1;
    if (clickchronicle_clickCount > clickchronicle_clickLimit) {
        clicks.removeChild(clicks.firstChild);
    }
    var newClick = document.createElement('a');
    newClick.setAttribute('href', url);
    var clickTitle = document.createTextNode(title);
    newClick.appendChild(clickTitle);
    clicks.appendChild(newClick);
}

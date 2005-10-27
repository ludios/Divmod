var clickchronicle_clickCount = 0;
var clickchronicle_clickLimit = 10;

function clickchronicle_setOpacity(node, ratio) {
    node.style.filter = 'alpha(opacity=' + new String(ratio * 100) + ')'
    node.style.opacity = ratio;
}

function clickchronicle_fadeIn(node, period) {
    var ratio = 0.0;
    function bump() {
        if (ratio < 1) {
            ratio += 0.2;
            clickchronicle_setOpacity(node, ratio);
            setTimeout(bump, 0.2);
        }
    }

    setTimeout(bump, 0.05);
}


function clickchronicle_createClick(title, url) {
    var newClick = document.createElement('div');
    var clickLink = document.createElement('a');
    var clickTitle = document.createTextNode(title);

    clickLink.setAttribute('href', url);
    clickLink.appendChild(clickTitle);
    newClick.appendChild(clickLink)

    clickchronicle_setOpacity(newClick, 0);

    clickchronicle_fadeIn(newClick, 2);

    return newClick;
}

function clickchronicle_incrementClickCounter() {
    var counter = document.getElementById('clicks-chronicled');
    var count = parseInt(counter.firstChild.nodeValue);
    counter.firstChild.nodeValue = count + 1;
}

function clickchronicle_addClick(title, url) {
    var nlc = document.getElementById('no-live-clicks-dialog');
    nlc.style.display = 'none';

    var clicks = document.getElementById('recent-clicks-container');
    clickchronicle_clickCount += 1;
    if (clickchronicle_clickCount > clickchronicle_clickLimit) {
        clicks.removeChild(clicks.lastChild);
    }
    clicks.insertBefore(clickchronicle_createClick(title, url), clicks.firstChild);
}

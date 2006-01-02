if(typeof(ClickChronicle) == "undefined") {
    ClickChronicle = {};
}

ClickChronicle.LiveClicks = Nevow.Athena.Widget.subclass();

ClickChronicle.LiveClicks.prototype.loaded = function() {
    this.clickCount = 0;
    this.clickLimit = 10;
    this.callRemote('getClickBacklog').addCallback(
        MochiKit.Base.bind(function(clicks){ this.addClicks(clicks) }, this));
}

ClickChronicle.LiveClicks.prototype.setOpacity = function(node, ratio) {
    node.style.filter = 'alpha(opacity=' + new String(ratio * 100) + ')';
    node.style.opacity = ratio;
}

ClickChronicle.LiveClicks.prototype.fadeIn = function(node, period) {
    var outerthis = this;
    var ratio = 0.0;
    function bump() {
        if (ratio < 1) {
            ratio += 0.2;
            outerthis.setOpacity(node, ratio);
            setTimeout(bump, 0.2);
        }
    }
    setTimeout(bump, 0.05);
}


ClickChronicle.LiveClicks.prototype.createClick = function(title, url) {
    var newClick = MochiKit.DOM.DIV({'class': 'click_' + this.clickCount},
                     MochiKit.DOM.A({'href': url}, title));

    this.setOpacity(newClick, 0);
    this.fadeIn(newClick, 2);

    return newClick;
}

ClickChronicle.LiveClicks.prototype.addClicks = function(clicks) {
    for(var i = 0; i < clicks.length; i++) {
        this.addClick.apply(this, clicks[i]);
    }
}

ClickChronicle.LiveClicks.prototype.addClick = function(title, url) {
    if(this.clickCount == 0) {
        MochiKit.DOM.hideElement(
            this.nodeByAttribute('class', 'big-title'));
    }

    this.clickCount++;

    if(this.clickLimit < this.clickCount) {
        this.node.removeChild(this.nodeByAttribute(
            'class', 'click_'+(this.clickCount-this.clickLimit)));
    }

    this.node.insertBefore(this.createClick(title, url), this.node.firstChild);
}

// import ClickChronicle
// import MochiKit.DOM

ClickChronicle.LiveClicks = Nevow.Athena.Widget.subclass('ClickChronicle.LiveClicks');
ClickChronicle.LiveClicks.methods(
    function loaded(self) {
        self.clickCount = 0;
        self.clickLimit = 10;
        self.callRemote('getClickBacklog').addCallback(
            function(clicks){ self.addClicks(clicks) });
    },

    function setOpacity(self, node, ratio) {
        node.style.filter = 'alpha(opacity=' + new String(ratio * 100) + ')';
        node.style.opacity = ratio;
    },

    function fadeIn(self, node, period) {
        var ratio = 0.0;
        function bump() {
            if (ratio < 1) {
                ratio += 0.2;
                self.setOpacity(node, ratio);
                setTimeout(bump, 0.2);
            }
        }
        setTimeout(bump, 0.05);
    },


    function createClick(self, title, url) {
        var newClick = MochiKit.DOM.DIV({'class': 'click_' + self.clickCount},
                         MochiKit.DOM.A({'href': url}, title));

        self.setOpacity(newClick, 0);
        self.fadeIn(newClick, 2);

        return newClick;
    },

    function addClicks(self, clicks) {
        for(var i = 0; i < clicks.length; i++) {
            self.addClick.apply(self, clicks[i]);
        }
    },

    function addClick(self, title, url) {
        if(self.clickCount == 0) {
            MochiKit.DOM.hideElement(
                self.nodeByAttribute('class', 'big-title'));
        }

        self.clickCount++;

        if(self.clickLimit < self.clickCount) {
            self.node.removeChild(self.nodeByAttribute(
                'class', 'click_'+(self.clickCount-self.clickLimit)));
        }

        self.node.insertBefore(self.createClick(title, url), self.node.firstChild);
    });

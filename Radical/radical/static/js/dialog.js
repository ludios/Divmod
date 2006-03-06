
// import Divmod
// import Radical

Radical.Dialog = {};

Radical.Dialog.Monolog = Divmod.Class.subclass('Radical.Dialog.Monolog');
Radical.Dialog.Monolog.methods(
    function __init__(self, parent, text) {
        self.parent = parent;
        self.text = text;
    },

    function display(self, duration) {
        self.node = document.createElement('span');
        self.node.style.background = '#aabbcc';
        self.node.style.opacity = 0.5;
        self.node.style.margin = '5px';
        self.node.appendChild(document.createTextNode(self.text));
        self.parent.appendChild(self.node);
        setTimeout(function() {
            self.parent.removeChild(self.node);
        }, duration);
    });


// import Nevow.Athena.Test
// import Divmod.Runtime

Divmod.Runtime.Tests.AppendNodeContent = Nevow.Athena.Test.TestCase.subclass('AppendNodeContent');
Divmod.Runtime.Tests.AppendNodeContent.methods(
    function test_appendNodeContent(self) {
        var html = '<div xmlns="http://www.w3.org/1999/xhtml">foo</div>';
        Divmod.Runtime.theRuntime.appendNodeContent(self.node, html);
        self.assertEquals(self.node.lastChild.tagName.toLowerCase(), 'div');
        self.assertEquals(self.node.lastChild.childNodes[0].nodeValue, 'foo');
        self.node.removeChild(self.node.lastChild);
    });

Divmod.Runtime.Tests.SetNodeContent = Nevow.Athena.Test.TestCase.subclass('SetNodeContent');
Divmod.Runtime.Tests.SetNodeContent.methods(
    function test_setNodeContent(self) {
        var html = '<div xmlns="http://www.w3.org/1999/xhtml">foo</div>';
        Divmod.Runtime.theRuntime.setNodeContent(self.node, html);
        self.assertEquals(self.node.childNodes.length, 1);
        self.assertEquals(self.node.firstChild.tagName.toLowerCase(), 'div');
        self.assertEquals(self.node.firstChild.childNodes[0].nodeValue, 'foo');
    });

Divmod.Runtime.Tests.AppendNodeContentScripts = Nevow.Athena.Test.TestCase.subclass('AppendNodeContentScripts');
Divmod.Runtime.Tests.AppendNodeContentScripts.methods(
    function test_appendNodeContentScripts(self) {
        Divmod.Runtime.Tests.AppendNodeContentScripts.runCount = 0;
        var html = (
            '<div xmlns="http://www.w3.org/1999/xhtml">' +
                '<script type="text/javascript">Divmod.Runtime.Tests.AppendNodeContentScripts.runCount++;</script>' +
                '<script type="text/javascript">Divmod.Runtime.Tests.AppendNodeContentScripts.runCount++;</script>' +
                '<script type="text/javascript">Divmod.Runtime.Tests.AppendNodeContentScripts.runCount++;</script>' +
           '</div>');
        Divmod.Runtime.theRuntime.appendNodeContent(self.node, html);
        self.assertEquals(Divmod.Runtime.Tests.AppendNodeContentScripts.runCount, 3);
    });

Divmod.Runtime.Tests.ElementSize = Nevow.Athena.Test.TestCase.subclass('ElementSize');
/* Tests for Runtime's getElementSize() method */
Divmod.Runtime.Tests.ElementSize.methods(
    function test_getElementSize(self) {
        var foo = self.nodeByAttribute("class", "foo");
        var size = Divmod.Runtime.theRuntime.getElementSize(foo);

        self.assertEquals(size.w, 1);
        self.assertEquals(size.h, 126);

        var bar = self.nodeByAttribute("class", "bar");

        size = Divmod.Runtime.theRuntime.getElementSize(bar);

        self.assertEquals(size.w, 2 + 70 + 4);
        self.assertEquals(size.h, 1 + 12 + 3);
    });

Divmod.Runtime.Tests.PageSize = Nevow.Athena.Test.TestCase.subclass('PageSize');
/* Tests for Runtime's getPageSize() method */
Divmod.Runtime.Tests.PageSize.methods(
    function test_getPageSize(self) {
        /* resizeTo isn't going to work for this, because of button panels
           and stuff - we know the viewport size, but we are changing the
           window size */

        var testWindow = window.open('', 'testWindow', 'width=480,height=640');
        var wsize = Divmod.Runtime.theRuntime.getPageSize(testWindow);

        self.assertEquals(wsize.w, 480);
        self.assertEquals(wsize.h, 640);

        testWindow.resizeBy(-16, -43);

        var newsize = Divmod.Runtime.theRuntime.getPageSize(testWindow);

        self.assertEquals(newsize.w, wsize.w-16);
        self.assertEquals(newsize.h, wsize.h-43);

        testWindow.resizeBy(16, 43);

        newsize = Divmod.Runtime.theRuntime.getPageSize(testWindow);
        testWindow.close();

        self.assertEquals(newsize.w, wsize.w);
        self.assertEquals(newsize.h, wsize.h);
    });

Divmod.Runtime.Tests.TraversalOrdering = Nevow.Athena.Test.TestCase.subclass('Divmod.Runtime.Tests.TraversalOrdering');
Divmod.Runtime.Tests.TraversalOrdering.methods(
    function test_traversalOrdering(self) {
        var classes = [];
        Divmod.Runtime.theRuntime.traverse(
            self.node,
            function(node) {
                if (node.className) {
                    classes.push(node.className);
                }
                return Divmod.Runtime.Platform.DOM_DESCEND;
            });

        self.assertEquals(classes[0], 'container');
        self.assertEquals(classes[1], 'left_child');
        self.assertEquals(classes[2], 'left_grandchild');
        self.assertEquals(classes[3], 'right_child');
        self.assertEquals(classes[4], 'right_grandchild');
    });

Divmod.Runtime.Tests.GetAttribute = Nevow.Athena.Test.TestCase.subclass('Divmod.Runtime.Tests.GetAttribute');
Divmod.Runtime.Tests.GetAttribute.methods(
    /**
     * Ensure that explicitly namespaced attributes and attributes whose
     * names get rewritten by IE can be correctly retrieved, and that they
     * don't interfere with each other if the local names are the same
     * (e.g. "class" and "athena:class" on a single node)
     */
    function test_getAttribute(self) {
        var node = document.createElement("div");
        node.className = "the class";
        self.node.appendChild(node);

        self.assertEquals(
            Divmod.Runtime.theRuntime.getAttribute(node, "class"),
            "the class");

        node.setAttribute("athena:class", "the athena class");

        self.assertEquals(
            Divmod.Runtime.theRuntime.getAttribute(node, "class"),
            "the class");

        self.assertEquals(
            Divmod.Runtime.theRuntime.getAttribute(
                node, "class", Nevow.Athena.XMLNS_URI, "athena"),
            "the athena class");

        self.assertEquals(
            Divmod.Runtime.theRuntime.getAttribute(node, "athena:class"),
            "the athena class");
    });

Divmod.Runtime.Tests.FindInRootNode = Nevow.Athena.Test.TestCase.subclass('Divmod.Runtime.Tests.FindInRootNode');
Divmod.Runtime.Tests.FindInRootNode.methods(
    function test_nodeByAttribute(self) {
        var node = Divmod.Runtime.theRuntime.nodeByAttribute(
            self.node, 'athena:class', 'Divmod.Runtime.Tests.FindInRootNode');
        self.assertEquals(self.node.id, node.id);
    },

    function test_firstNodeByAttribute(self) {
        var firstNode = Divmod.Runtime.theRuntime.firstNodeByAttribute(
            self.node, 'athena:class', 'Divmod.Runtime.Tests.FindInRootNode');
        self.assertEquals(self.node.id, firstNode.id);
    },

    function test_nodesByAttribute(self) {
        var nodes = Divmod.Runtime.theRuntime.nodesByAttribute(
            self.node, 'athena:class', 'Divmod.Runtime.Tests.FindInRootNode');
        self.assertEquals(self.node.id, nodes[0].id);
    },

    /**
     * Assert that using nodeByAttribute to look for a node with an attribute
     * value which is not present throws the proper error, NodeAttributeError.
     */
    function test_nodeByAttributeMissing(self) {
        var error = self.assertThrows(
            Divmod.Runtime.NodeAttributeError,
            function() {
                Divmod.Runtime.theRuntime.nodeByAttribute(
                    self.node, 'foo', 'bar');
            });
        self.assertEqual(error.root, self.node);
        self.assertEqual(error.attribute, 'foo');
        self.assertEqual(error.value, 'bar');
    },

    /**
     * Assert that using firstNodeByAttribute to look for a node with an
     * attribute value which is not present throws the proper error,
     * NodeAttributeError.
     */
    function test_firstNodeByAttributeMissing(self) {
        var error = self.assertThrows(
            Divmod.Runtime.NodeAttributeError,
            function() {
                Divmod.Runtime.theRuntime.firstNodeByAttribute(
                    self.node, 'foo', 'bar');
            });
        self.assertEqual(error.root, self.node);
        self.assertEqual(error.attribute, 'foo');
        self.assertEqual(error.value, 'bar');
    });

// ==UserScript==
// @name          ClickChronicle
// @namespace     http://clickchronicle.com/
// @description   Capture surfing to ClickChronicle
// @include       *
// @exclude       *divmod.com*, *.clickchronicle.com
// ==/UserScript==

(function() {
    const POST_INTERCEPT = 'HistoryIntercept';
    var intercept_on = true;
   
    interceptor_setup();

    // The actual work!
    // Post the URL to the divmod server
    if(intercept_on){
      GM_xmlhttpRequest({ method:"POST",
			    url:'http://clickchronicle.com/private/record' +
		            '?url=' + escape(document.location.href) +
			    '&title=' + escape(document.title),
			    
			    onload:function(result) {
			    GM_log(result.status + ' ' + result.statusText + ' ' +
				   document.location.href + ' ' +
				   document.title)
			      }
			})
	}

    // Everything below is to display and manage the little recording toggle
    // at the bottom of each page.
    //
    // Code copied from Post Intereceptor:
    // http://www.mozdev.org/pipermail/greasemonkey/2005-April/001319.html

    function toggle_intercept(flag)
    {
	intercept_on = flag;
	GM_setValue(POST_INTERCEPT, intercept_on);
	setup_pi_button();
    }

    function setup_pi_button()
    {
	var pi = document.getElementById('__pi_toggle');
	if (!pi) {
	    pi = new_node('span', '__pi_toggle');
	    pi.textContent = '[PI]';
	    document.getElementsByTagName('body')[0].appendChild(pi);
	    pi.addEventListener('click',
				function() {toggle_intercept(!intercept_on)},
				false);

	    var pi_toggle_style = ' \
#__pi_toggle { \
  position: fixed; \
  bottom: 0; right: 0; \
  display: inline; \
  padding: 1px; \
  font: caption; \
  font-weight: normal; \
  font-size: x-small;  \
  cursor: crosshair; \
} \
#__pi_toggle:hover { \
  border-width: 1px 0 0 1px; \
  border-style: solid none none solid; \
  border-color: black; \
} \
';
	    add_style("__pi_toggle_style", pi_toggle_style);
	}

	if (intercept_on) {
	    pi.textContent = 'DH On';
	    pi.setAttribute('title', 'Click to turn Divmod History Recording Off');
	    pi.style.backgroundColor = '#0c2369';
	    pi.style.color = '#ddff00';
	} else {
	    pi.textContent = 'DH Off';
	    pi.setAttribute('title', 'Click to turn Divmod History Recoding On');
	    pi.style.backgroundColor = '#ccc';
	    pi.style.color = '#888';
	}
    }

    function interceptor_setup()
    {
      intercept_on = GM_getValue(POST_INTERCEPT, false);
      GM_log('intercept_on = ' + intercept_on);
      setup_pi_button();
    }

    // helper functions
    function new_node(type, id)
    {
	var node = document.createElement(type);
	if (id && id.length > 0)
	    node.id = id;
	return node;
    }

    function new_text_node(txt)
    {
	return document.createTextNode(txt);
    }

    function add_style(style_id, style_rules)
    {
	if (document.getElementById(style_id))
	    return;

	var style = new_node("style", style_id);
	style.type = "text/css";
	style.innerHTML = style_rules;
	document.getElementsByTagName('head')[0].appendChild(style);
    }


 })();

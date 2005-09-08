from xmantissa import webtheme
from nevow import tags

class ClickChronicleTheme(webtheme.XHTMLDirectoryTheme):
    def head(self):
        return tags.link(rel="stylesheet", type="text/css", 
                         href="/static/css/clickchronicle.css")
        

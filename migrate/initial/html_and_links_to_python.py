#!/usr/bin/python

# Copies current contents of HtmlChunk and MenuLink
# tables to python script -- use this to update migrate_html.py

import devel
from cciw.cciwmain.models import HtmlChunk, MenuLink

output = []
output.append("html = []\n")

h_template = "html.append((%r, %r, %r, %r))\n"
for h in HtmlChunk.objects.all():
    if h.menu_link_id is None:
        menu_link_url = ''
    else:
        menu_link_url = h.menu_link.url
    
    output.append(h_template % (h.name, menu_link_url, h.page_title, h.html))

output.append("links = (")
l_template = "   (%r, %r, %r, %r),"
for l in MenuLink.objects.all():
    if l.parent_item_id is None:
        parent_link_url = ''
    else:
        parent_link_url = l.parent_item.url
    
    output.append(l_template % (l.title, l.url, l.listorder, parent_link_url))

output.append(")")

print '\n'.join(output)


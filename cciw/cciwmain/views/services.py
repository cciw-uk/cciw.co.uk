from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings
from django.shortcuts import render
from django.utils.safestring import mark_safe

options = ['output-format=html',
           'include-footnotes=0'  # otherwise we'll have to strip them out in the javascript function.
           ]
options = '&'.join(options)
esv_base_url = 'http://www.gnpcb.org/esv/share/get/?key=%(key)s&action=doPassageQuery&%(options)s&%%s' %  \
               {'key': settings.ESV_KEY, 'options': options}


def esv_passage(request):
    passage = request.GET.get('passage', '')
    url = esv_base_url % urlencode({'passage': passage})
    page = urlopen(url)
    c = {}
    c['title'] = "Bible passage lookup"
    c['passagetext'] = mark_safe(page.read().decode('utf-8'))
    c['passage'] = passage
    return render(request, 'cciw/services/esv_passage.html', c)

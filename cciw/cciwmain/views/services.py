import urllib
from django.conf import settings
from django import shortcuts
from django.template import RequestContext
from cciw.cciwmain.common import standard_extra_context

options = [ 'output-format=html',
            'include-footnotes=0' # otherwise we'll have to strip them out in the javascript function.
        ]
options = '&'.join(options)
esv_base_url = 'http://www.gnpcb.org/esv/share/get/?key=%(key)s&action=doPassageQuery&%(options)s&%%s' %  \
                    {'key': settings.ESV_KEY, 'options': options}

def esv_passage(request):
    passage = request.GET.get('passage', '')
    url = esv_base_url % urllib.urlencode({'passage':passage})
    page = urllib.urlopen(url)
    c = standard_extra_context(title="Bible passage lookup")
    c['passagetext'] = page.read()
    c['passage'] = passage
    return shortcuts.render_to_response('cciw/services/esv_passage.html',
            context_instance=RequestContext(request, c))

    

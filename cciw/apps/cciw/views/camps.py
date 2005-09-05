from django.core import template_loader
from django.core.extensions import DjangoContext as Context
from django.models.camps import camps
from django.utils.httpwrappers import HttpResponse

from cciw.apps.cciw.common import Page


def index(request):
	all_camps = camps.get_list(order_by=['-year','number'])
	years = [camp.year for camp in all_camps]
	uniqueyears = []
	for year in years:
		if not year in uniqueyears: uniqueyears.append(year)
	t = template_loader.get_template('camps/index')
	p = Page(request, title="Camps")
	c = Context(request, {'camps': all_camps, 
						'page': p,
						'years': uniqueyears});
	return HttpResponse(t.render(c))
	

	
	

from django.core import template_loader

from django.models.camps import camps
from django.utils.httpwrappers import HttpResponse
from django.core.exceptions import Http404
from cciw.apps.cciw.common import StandardContext

def index(request, year = None):
	if (year == None):
		all_camps = camps.get_list(order_by=['-year','number'])
		years = [camp.year for camp in all_camps]
		uniqueyears = []
		for year in years:
			if not year in uniqueyears: uniqueyears.append(year)
	else:
		year = int(year)  # year is result of regex match
		uniqueyears = [year]
		all_camps = camps.get_list(year__exact=year, order_by=['number'])
		if len(all_camps) == 0:
			raise Http404
	
	t = template_loader.get_template('camps/index')
	c = StandardContext(request, {'camps': all_camps, 
						'years': uniqueyears},
					title="Past Camps")
	return HttpResponse(t.render(c))

def detail(request, year, number):
	year = int(year)
	number = int(number)
	try:
		camp = camps.get_object(year__exact=year, number__exact=number)
	except camps.CampDoesNotExist:
		raise Http404
		
	t = template_loader.get_template('camps/detail')
	c = StandardContext(request, {'camp': camp }, 
							title = camp.niceName)
	return HttpResponse(t.render(c))

	

	
	

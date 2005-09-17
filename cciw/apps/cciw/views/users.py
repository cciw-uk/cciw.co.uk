from django.views.generic import list_detail
from django.utils.httpwrappers import HttpResponse
from django.core.exceptions import Http404
from django.core import template_loader

from django.models.users import users
from cciw.apps.cciw.common import *

def index(request):
	lookup_args = {'dummyUser__exact' : 'False', 'hidden__exact': 'False'} # TODO - depends on authorisation
	order_options = \
		{'adj': 'dateJoined',
		'ddj': '-dateJoined',
		'aun': 'userName',
		'dun': '-userName',
		'arn': 'realName',
		'drn': '-realName',
		'als': 'lastSeen',
		'dls': '-lastSeen'}
	order_request = request.GET.get('o', None)
	try:
		order_by = order_options[order_request]
	except:
		order_by = 'userName'
	lookup_args['order_by'] = (order_by,)
	try:
		search = '%' + request['search'] + '%'
		lookup_args['where'] = ["(userName LIKE %s OR realName LIKE %s)"]
		lookup_args['params'] = [search, search]
	except KeyError:
		pass

	
	return list_detail.object_list(request, 'users', 'users', 
		extra_context =  standard_extra_context(request, title='Members'), 
		template_name = 'members/index',
		paginate_by=100, extra_lookup_kwargs = lookup_args,
		allow_empty = True)

def detail(request, userName):
	try:
		user = users.get_object(userName__exact = userName)
	except users.UserDoesNotExist:
		raise Http404
	
	c = StandardContext(request, title="Members: " + user.userName)
	c['user'] = user
	c['awards'] = user.get_personalAward_list()
	t = template_loader.get_template('members/detail')
	return HttpResponse(t.render(c))

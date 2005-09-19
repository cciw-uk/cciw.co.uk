from django.views.generic import list_detail
from django.utils.httpwrappers import HttpResponse, HttpResponseRedirect
from django.core.exceptions import Http404
from django.core import template_loader

from django.models.members import members
from cciw.apps.cciw.common import *
from django.core.extensions import DjangoContext

def index(request):
	lookup_args = {'dummyMember__exact' : 'False', 'hidden__exact': 'False'} # TODO - depends on authorisation
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
		
	return list_detail.object_list(request, 'members', 'members', 
		extra_context =  standard_extra_context(request, title='Members'), 
		template_name = 'members/index',
		paginate_by=50, extra_lookup_kwargs = lookup_args,
		allow_empty = True)

def detail(request, userName):
	try:
		member = members.get_object(userName__exact = userName)
	except members.MemberDoesNotExist:
		raise Http404
	
	c = StandardContext(request, title="Members: " + member.userName)
	c['member'] = member
	c['awards'] = member.get_personalAward_list()
	t = template_loader.get_template('members/detail')
	return HttpResponse(t.render(c))

	
def login(request):
	c = StandardContext(request, title="Login")
	if request.POST:
		try:
			member = members.get_object(userName__exact = request.POST['userName'])
			if member.checkPassword(request.POST['password']):
				request.session['member_id'] = member.id
				return HttpResponseRedirect(member.get_absolute_url())
			else:
				c['loginFailed'] = True
		except members.MemberDoesNotExist:
			c['loginFailed'] = True
	t = template_loader.get_template('members/login')
	return HttpResponse(t.render(c))

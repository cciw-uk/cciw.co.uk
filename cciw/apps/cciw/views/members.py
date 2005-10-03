from django.views.generic import list_detail
from django.utils.httpwrappers import HttpResponseRedirect
from django.core.exceptions import Http404
from django.core import template_loader
from django.core.extensions import render_to_response

from django.models.members import members
from django.models.members.members import MemberDoesNotExist
from cciw.apps.cciw.common import *
from django.core.extensions import DjangoContext
from datetime import datetime, timedelta

def index(request):
	# TODO - depends on authorisation
	lookup_args = {'dummyMember__exact' : 'False', 'hidden__exact': 'False'} 
	if (request.GET.has_key('online')):
		lookup_args['lastSeen__gte'] = datetime.now() - timedelta(minutes=3)
	
	order_option_to_lookup_arg(
		{'adj': 'dateJoined',
		'ddj': '-dateJoined',
		'aun': 'userName',
		'dun': '-userName',
		'arn': 'realName',
		'drn': '-realName',
		'als': 'lastSeen',
		'dls': '-lastSeen'},
		lookup_args, request, 'userName')
		
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
	except MemberDoesNotExist:
		raise Http404
	
	if request.POST:
		if request.POST.has_key('logout'):
			del request.session['member_id']
		
	c = StandardContext(request, title="Members: " + member.userName)
	c['member'] = member
	c['awards'] = member.get_personalAward_list()
	return render_to_response('members/detail', c)
	
def login(request):
	c = StandardContext(request, title="Login")
	if request.POST:
		try:
			member = members.get_object(userName__exact = request.POST['userName'])
			if member.checkPassword(request.POST['password']):
				request.session['member_id'] = member.userName
				member.lastSeen = datetime.now()
				member.save()
				return HttpResponseRedirect(member.get_absolute_url())
			else:
				c['loginFailed'] = True
		except MemberDoesNotExist:
			c['loginFailed'] = True
	return render_to_response('members/login', c)

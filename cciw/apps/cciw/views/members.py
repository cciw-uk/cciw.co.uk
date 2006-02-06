from django.views.generic import list_detail
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext

from cciw.apps.cciw.models import Member
from cciw.apps.cciw.common import *
from datetime import datetime, timedelta

def index(request):
    # TODO - depends on authorisation
    lookup_args = {'dummy_member' : 'False', 'hidden': 'False'} 
    if (request.GET.has_key('online')):
        lookup_args['last_seen__gte'] = datetime.now() - timedelta(minutes=3)
    
    extra_context = standard_extra_context(title='Members')
    order_option_to_lookup_arg(
        {'adj': ('date_joined',),
        'ddj': ('-date_joined',),
        'aun': ('user_name',),
        'dun': ('-user_name',),
        'arn': ('real_name',),
        'drn': ('-real_name',),
        'als': ('last_seen',),
        'dls': ('-last_seen',)},
        lookup_args, request, ('user_name',))
    extra_context['default_order'] = 'aun'
    
    try:
        search = '%' + request['search'] + '%'
        lookup_args['where'] = ["(user_name LIKE %s OR real_name LIKE %s)"]
        lookup_args['params'] = [search, search]
    except KeyError:
        pass
        
    return list_detail.object_list(request, model=Member, 
        extra_context = extra_context, 
        template_name = 'cciw/members/index',
        paginate_by=50, extra_lookup_kwargs = lookup_args,
        allow_empty = True)

def detail(request, user_name):
    try:
        member = Member.objects.get(user_name=user_name)
    except Member.DoesNotExist:
        raise Http404
    
    if request.POST:
        if request.POST.has_key('logout'):
            try:
                del request.session['member_id']
            except KeyError:
                pass
        
    c = RequestContext(request, 
        standard_extra_context(title="Members: " + member.user_name))
    c['member'] = member
    c['awards'] = member.personal_awards.all()
    return render_to_response('cciw/members/detail', c)
    
def login(request):
    c = RequestContext(request, standard_extra_context(title="Login"))
    c['referrer'] = request.META.get('HTTP_REFERER', None)
    if request.POST:
        try:
            member = Member.objects.get(user_name=request.POST['user_name'])
            if member.check_password(request.POST['password']):
                request.session['member_id'] = member.user_name
                member.last_seen = datetime.now()
                member.save()
                return HttpResponseRedirect(member.get_absolute_url())
            else:
                c['loginFailed'] = True
        except Member.DoesNotExist:
            c['loginFailed'] = True
    return render_to_response('cciw/members/login', c)

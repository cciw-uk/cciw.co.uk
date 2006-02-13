from django.views.generic import list_detail
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext

from cciw.apps.cciw.models import Member
from cciw.apps.cciw.common import *
from datetime import datetime, timedelta

def index(request):
    
    members = Member.objects.filter(dummy_member=False, hidden=False) # TODO - depends on authorisation
    if (request.GET.has_key('online')):
        members = members.filter(last_seen__gte=(datetime.now() - timedelta(minutes=3)))
    
    extra_context = standard_extra_context(title='Members')
    order_by = get_order_option(
        {'adj': ('date_joined',),
        'ddj': ('-date_joined',),
        'aun': ('user_name',),
        'dun': ('-user_name',),
        'arn': ('real_name',),
        'drn': ('-real_name',),
        'als': ('last_seen',),
        'dls': ('-last_seen',)},
        request, ('user_name',))
    members = members.order_by(*order_by)
    extra_context['default_order'] = 'aun'

    try:
        search = request['search']
        if len(search) > 0:
            members = (members.filter(user_name__icontains=search) | members.filter(real_name__icontains=search))
    except KeyError:
        pass

    return list_detail.object_list(request, members,
        extra_context=extra_context, 
        template_name='cciw/members/index',
        paginate_by=50,
        allow_empty=True)

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

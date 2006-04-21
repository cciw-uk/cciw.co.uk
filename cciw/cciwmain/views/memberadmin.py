"""Administrative views for members (signup, password change etc)"""
from django import shortcuts
from django import template
from django.core import validators
from cciw.cciwmain.common import standard_extra_context

def signup(request):
    c = template.RequestContext(request, standard_extra_context(title="Sign up"))
    
    if request.POST.get("agreeterms", None) is not None:
        c['stage'] = "email"
    elif "email" in request.POST or "submitemail" in request.POST:
        email = request.POST['email']
        c['email'] = email
        if validators.email_re.search(email):
            # TODO - send e-mail
            c['stage'] = "emailsubmitted"
        else:
            c['stage'] = "email"
            c['error_message'] = "Please enter a valid e-mail address"
    else:
        c['stage'] = "start"
    return shortcuts.render_to_response('cciw/members/signup.html', 
        context_instance=c)


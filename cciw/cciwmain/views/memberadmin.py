"""Administrative views for members (signup, password change etc)"""
from django import shortcuts, template
from django.core import validators, mail
from django.contrib.sites.models import Site
from django.conf import settings
from cciw.cciwmain.common import standard_extra_context
from cciw.cciwmain.models import Member
from cciw.middleware.threadlocals import set_current_member
import md5
import urllib
import re
import datetime


username_re = re.compile(r'^[A-Za-z0-9_]{3,15}$')
password_re = re.compile(r'^[A-Za-z0-9]{5,15}$')

class ValidationError(Exception):
    pass

# TODO - add synchronize lock here
def create_user(user_name, password1, password2):
    if username_re.match(user_name) is None:
        raise ValidationError("The user name is invalid, please check and try again")
    elif Member.all_objects.filter(user_name__iexact=user_name).count() > 0:
        # Can't just try to create it and catch exceptions,
        # since the ORM checks to see if the primary key is already used
        # and does an 'update' instead of 'insert' in that case.  Also
        # we want to catch usernames that vary only by case
        raise ValidationError("The user name is already used.  Please choose another.")
    elif password_re.match(password1) is None:
        raise ValidationError("The password entered does not match the requirements, please try again.")
    elif password2 !=  password1:
        raise ValidationError("The passwords do not match")
    else:
        m = Member(user_name=user_name, 
                   last_seen=datetime.datetime.now(),
                   date_joined=datetime.datetime.now(),
                   password=Member.encrypt_password(password1))
        m.save()
        return m

def email_hash(email):
    """Gets a hash of an email address, to be used in the sign process"""
    # Use every other character to make it shorter and friendlier
    return md5.new(settings.SECRET_KEY + email).hexdigest()[::2]

def email_address_used(email):
    return Member.all_objects.filter(email__iexact=email).count() != 0

def validate_email_and_hash(email, hash):
    if email_address_used(email):
        # in reality shouldn't get here, unless user has 
        # started two signup processes in parallel
        return (False, """The e-mail address is already used.  You must start the 
 sign-up procedure again with a different e-mail address.""")
    elif email_hash(email) != hash:
        return (False, """The e-mail address was not confirmed.  Please
 ensure you have copied the URL from the e-mail correctly.""")
    else:
        return (True, '')
        
def send_signup_mail(email):
    domain = Site.objects.get_current().domain
    mail.send_mail("CCIW - Sign-up instructions",
"""Thank you for beginning the sign-up process on the CCIW website

To confirm the e-mail address you used is genuine and continue the 
sign-up process, please click on the link below:

http://%(domain)s/signup/?email=%(email)s&h=%(hash)s

If clicking on the link does not do anything, please copy and paste
the link into your web browser.

----
If you did not attempt to sign up on the CCIW web-site, you can just
ignore this e-mail.

""" % {'domain': domain, 'email': urllib.quote(email), 'hash': email_hash(email)},
"website@cciw.co.uk", [email])


def signup(request):
    c = standard_extra_context(title="Sign up")
    
    if not request.POST and not request.GET:
        ######## 1. START #########
        c['stage'] = "start"
    
    if "agreeterms" in request.POST:
        ######## 2. ENTER EMAIL #########
        c['stage'] = "email"
        
    elif "email" in request.POST or "submit_email" in request.POST:
        ######## 3. CHECK ADDRESS AND SEND EMAIL #########
        email = request.POST['email'].strip()
        c['email'] = email
        if validators.email_re.search(email):
            if email_address_used(email):
                c['stage'] = "email"
                c['alreadyused'] = True
            else:
                try:
                    send_signup_mail(email)
                except Exception, e:
                    c['error_message'] = \
                        """E-mail could not be sent for the following reason: %s
                        If the error persists, please contact the webmaster.""" % str(e)
                    c['stage'] = "email"
                else:
                    c['stage'] = "emailsubmitted"
        else:
            c['stage'] = "email"
            c['error_message'] = "Please enter a valid e-mail address"

    elif "email" in request.GET:
        ######## 4. USERNAME AND PASSWORD #########
        email = request.GET['email']
        hash = request.GET.get('h', '')
        valid, msg = validate_email_and_hash(email, hash)
        if valid:
            c['stage'] = "user_name"
            c['confemail'] = email
            c['confhash'] = hash
        else:
            c['stage'] = 'invalid'
            c['error_message'] = msg
    
    elif "user_name" in request.POST or "submit_user_name" in request.POST:
        ######## 5. CREATE ACCOUNT #########
        # First, re-check email and hash in case of 
        # tampering with hidden form values
        email = request.POST.get('confemail', '')
        hash = request.POST.get('confhash', '')
        valid_email, msg = validate_email_and_hash(email, hash)
        if valid_email:
            # Check username and password
            user_name = request.POST.get('user_name', '')
            try:
                m = create_user(user_name,
                                request.POST.get('password1', ''),
                                request.POST.get('password2', ''))
            except ValidationError, e:
                c['stage'] = "user_name"
                c['confemail'] = email
                c['confhash'] = hash
                c['user_name'] = user_name
                c['error_message'] = str(e)
            else:
                m.email = email
                m.save()
                request.session['member_id'] = m.user_name
                set_current_member(m)
                c['stage'] = 'end'
        else:
            c['stage'] = 'invalid'
            c['error_message'] = msg

    ## Do this at end, so that the context_processors
    ## are executed after set_current_member
    c = template.RequestContext(request, c)

    return shortcuts.render_to_response('cciw/members/signup.html', 
        context_instance=c)


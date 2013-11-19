"""Administrative views for members (signup, password change etc)"""
from django.shortcuts import render
from django.core import mail
from django.contrib import messages
from django.conf import settings
from django.core.urlresolvers import reverse
from django.forms import widgets
from django.http import Http404, HttpResponseRedirect
from django.utils.crypto import salted_hmac
from django.views.generic.edit import ModelFormMixin
from django import forms
from cciw.cciwmain.common import DefaultMetaData, AjaxyFormView, member_username_re
from cciw.forums.models import Member
from cciw.middleware.threadlocals import set_member_session, get_current_member
from cciw.cciwmain.decorators import member_required
from cciw.cciwmain import common
from cciw.cciwmain import imageutils
from cciw.cciwmain.forms import CciwFormMixin
from cciw.cciwmain.utils import is_valid_email
import urllib
import re
import datetime
import string
import random
import base64

password_re = re.compile(r'^[A-Za-z0-9]{5,15}$')

# The number of days a new password must be activated within
# (this is to stop an old e-mail being used to reset a password,
# in the scenario where an attacker has temporary access to
# a user's e-mails).
NEW_PASSWORD_EXPIRY = 5


class ValidationError(Exception):
    pass


# Ideally would add synchronize lock here, but YAGNI with any imaginable amount of traffic
def create_user(user_name, password1, password2):
    if member_username_re.match(user_name) is None:
        raise ValidationError("The user name is invalid, please check and try again")
    elif Member.all_objects.filter(user_name__iexact=user_name).exists():
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
        iconfilename = user_name + "." + settings.DEFAULT_MEMBER_ICON.split('.')[-1]
        m = Member(user_name=user_name,
                   last_seen=datetime.datetime.now(),
                   date_joined=datetime.datetime.now(),
                   password=Member.encrypt_password(password1),
                   icon="%s/%s" % (settings.MEMBER_ICON_PATH, iconfilename))
        m.save()

        # Copy default member icon
        import shutil
        shutil.copy("%s/%s" % (settings.STATIC_ROOT, settings.DEFAULT_MEMBER_ICON),
                    "%s/%s/%s" % (settings.MEDIA_ROOT, settings.MEMBER_ICON_PATH, iconfilename))
        return m


def email_hash(email):
    """Gets a hash of an email address, to be used in the signup process"""
    # Use every other character to make it shorter and friendlier
    return salted_hmac("cciw.cciwmain.memberadmin.signupemail", email).hexdigest()[::2]


def email_address_used(email):
    return Member.all_objects.filter(email__iexact=email).count() != 0


def random_password():
    chars = list(string.lowercase)
    random.shuffle(chars)
    return ''.join(chars[0:8])


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


def email_and_username_hash(email, user_name):
    """Gets a hash of an email address + user_name"""
    # Use every other character to make it shorter and friendlier
    return salted_hmac("cciw.cciwmain.memberadmin.changeemail", email + ":" + user_name).hexdigest()[::2]

def validate_email_username_and_hash(email, user_name, hash):
    if email_address_used(email):
        return (False, """The e-mail address is already in use.""")
    elif email_and_username_hash(email, user_name) != hash:
        return (False, """The e-mail address was not confirmed.  Please
 ensure you have copied the URL from the e-mail correctly.""")
    else:
        return (True, '')


def send_signup_mail(email):
    mail.send_mail("CCIW - Sign-up instructions",
"""Thank you for beginning the sign-up process on the CCIW website

To confirm the e-mail address you used is genuine and continue the
sign-up process, please click on the link below:

https://%(domain)s/signup/?email=%(email)s&h=%(hash)s

If clicking on the link does not do anything, please copy and paste
the link into your web browser.

----
If you did not attempt to sign up on the CCIW web-site, you can just
ignore this e-mail.

""" % {'domain': common.get_current_domain(), 'email': urllib.quote(email), 'hash': email_hash(email)},
                   settings.SERVER_EMAIL, [email])


def send_username_reminder(member):
    mail.send_mail("CCIW - user name reminder",
"""You requested a user name reminder on the CCIW website.
Your user name is: %(user_name)s

You can log in at:
https://%(domain)s/login/

Thanks.
""" % {'domain': common.get_current_domain(), 'user_name': member.user_name },
    settings.SERVER_EMAIL, [member.email])


def send_newpassword_email(member):
    # Create a new password
    password = random_password()
    hash = create_new_password_hash(password, member.user_name)

    mail.send_mail("CCIW - new password.",
"""You have requested a new password for your login on the CCIW website.
Your new password is:

    %(password)s

In order to activate this new password, please click on the link below:

https://%(domain)s/memberadmin/change-password/?u=%(user_name)s&h=%(hash)s

If clicking on the link does not do anything, please copy and paste the
entire link into your web browser.

After activating the password, it is suggested that you log in using the
above password and then change your password to one more memorable.

If you did not request a new password on the CCIW website, then do not click
on the link:  this e-mail has been triggered by someone else entering your
e-mail addess and asking for a new password.  The password will not actually
be changed until you click the link, so you can safely ignore this e-mail.

""" % {'domain': common.get_current_domain(), 'user_name': member.user_name,
       'password': password, 'hash': hash},
    settings.SERVER_EMAIL, [member.email])


def create_new_password_hash(password, user_name):
    # Create string used to verify user_name and date.
    hash_str = u':'.join([datetime.date.today().isoformat(), user_name, password])
    return base64.urlsafe_b64encode(hash_str.encode("utf-8"))


def extract_new_password(hash, user_name):
    """Extracts the new password from the hash, throwing a ValidationError
    containing an error message if it fails."""
    invalid_url_msg = "The URL hash was invalid -- please check that you " + \
        "copied the entire URL from the e-mail"

    try:
        hash_str = base64.urlsafe_b64decode(hash.encode("ascii"))
    except TypeError:
        raise ValidationError(invalid_url_msg)
    try:
        date_str, h_user_name, password = hash_str.split(':')
    except ValueError:
        raise ValidationError(invalid_url_msg)

    try:
        year, month, day = map(int, date_str.split('-'))
        email_date = datetime.date(year, month, day)
    except ValueError: # catches unpacking, int, and datetime.date
        raise ValidationError(invalid_url_msg)

    if (datetime.date.today() - email_date).days > NEW_PASSWORD_EXPIRY:
        raise ValidationError("The new password has expired.  Please request a new password again.")

    if (h_user_name != user_name):
        # hack attempt?
        raise ValidationError("This URL has been tampered with.  Password not changed.")

    return password


def send_newemail_email(member, new_email):
    mail.send_mail("CCIW - E-mail change",
"""You have changed your e-mail address on the CCIW website.

To confirm that your new e-mail address is genuine and update our records,
please click on the link below:

https://%(domain)s/memberadmin/change-email/?email=%(email)s&u=%(user_name)s&h=%(hash)s

If clicking on the link does not do anything, please copy and paste
the entire link into your web browser.

""" % {'domain': common.get_current_domain(), 'email': urllib.quote(new_email),
       'user_name': urllib.quote(member.user_name),
       'hash': email_and_username_hash(new_email, member.user_name)},
    settings.SERVER_EMAIL, [new_email])


#################  VIEW FUNCTIONS #####################

def signup(request):
    c = dict(title="Sign up")

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
        if is_valid_email(email):
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
                set_member_session(request, m)
                c['stage'] = 'end'
        else:
            c['stage'] = 'invalid'
            c['error_message'] = msg

    # RequestContext should be created at the end, so that the
    # context_processors are executed after set_member_session
    return render(request, 'cciw/members/signup.html', c)


def help_logging_in(request):
    """View that has reset password and username reminder functionality."""
    c = dict(title="Logging in problems.")
    if request.method == 'POST':
        # Check e-mail
        email = request.POST.get('email', '').strip()
        c['email'] = email
        cont = True
        if not is_valid_email(email):
            c['error_message'] = "The e-mail address is not valid.  Please check and try again."
            cont = False

        # Check e-mail in db
        if cont:
            # Temporary - use [0] instead of .get() because of some bad data
            try:
                member = Member.objects.filter(email__iexact=email)[0]
            except IndexError:
                c['error_message'] = "A member with that e-mail address could not be found."
                cont = False

        if cont:
            if request.POST.has_key('usernamereminder'):
                send_username_reminder(member)
                c['success_message'] = "An e-mail has been sent with a reminder of your user name."
            elif request.POST.has_key('newpassword'):
                send_newpassword_email(member)
                c['success_message'] = "An e-mail has been sent to you with a new password."

    return render(request, 'cciw/members/help_logging_in.html', c)


def change_password(request):
    """View that handles password changes, with a form and from
    'new password' emails."""
    user_name = request.GET.get('u', '')
    hash = request.GET.get('h', '')

    c = dict(title="Change password")
    if user_name:
        # New password from e-mail
        try:
            password = extract_new_password(hash, user_name)
        except ValidationError, e:
            c['error_message'] = e.args[0]
        else:
            try:
                member = Member.objects.get(user_name=user_name)
            except Member.DoesNotExist:
                # unlikely!
                raise Http404
            member.password = Member.encrypt_password(password)
            member.save()
            c['success_message'] = "Password changed."
    else:
        # form for logged in member
        current_member = get_current_member()
        if current_member is None:
            return HttpResponseRedirect("/login/?r=%s" % request.path)
        c['show_form'] = True
        if request.method == 'POST':
            new_password = request.POST.get('new_password', '')
            new_password2 = request.POST.get('new_password2', '')
            error_message = ''
            if not (20 >= len(new_password) >= 5):
                error_message = "Your password must be between 5 and 20 characters."
            elif new_password != new_password2:
                error_message = "The two passwords do not match."
            if not error_message:
                current_member.password = Member.encrypt_password(new_password)
                current_member.save()
                c['success_message'] = "Password changed."
            else:
                c['error_message'] = error_message

    return render(request, 'cciw/members/change_password.html', c)


def change_email(request):
    """View that responds to links in the 'change e-mail' emails."""
    c = dict(title="Change email")

    user_name = request.GET.get('u')
    email = request.GET.get('email', '')
    hash = request.GET.get('h', '')
    valid, msg = validate_email_username_and_hash(email, user_name, hash)
    if valid:
        try:
            member = Member.objects.filter(user_name=user_name)[0]
        except IndexError:
            c['error_message'] = "The user name is unknown"
        else:
            member.email = email
            member.save()
        c['success_message'] = "New email address confirmed, thank you."
    else:
        c['error_message'] = msg

    return render(request, 'cciw/members/change_email.html', c)


preferences_fields = ["real_name", "email", "show_email", "comments", "message_option", "icon"]
class PreferencesForm(CciwFormMixin, forms.ModelForm):
    real_name = forms.CharField(widget=forms.TextInput(attrs={'size':str(Member._meta.get_field('real_name').max_length)}),
                                label="Real name", required=False,
                                max_length=Member._meta.get_field('real_name').max_length)
    email = forms.EmailField(widget=forms.TextInput(attrs={'size':'40'}))
    message_option = forms.ChoiceField(choices=Member.MESSAGE_OPTIONS,
                                       widget=forms.RadioSelect,
                                       label="Message storing")
    icon = forms.FileField(widget=widgets.FileInput,
                           label="Icon", required=False)

    class Meta:
        model = Member
        fields = preferences_fields

PreferencesForm.base_fields.keyOrder = preferences_fields


class Preferences(DefaultMetaData, AjaxyFormView, ModelFormMixin):
    metadata_title = u"Preferences"
    form_class = PreferencesForm
    template_name = 'cciw/members/preferences.html'

    def get_success_url(self):
        return reverse("cciwmain.memberadmin.preferences")

    def dispatch(self, request):
        current_member = get_current_member()
        self.orig_email = current_member.email # before update
        self.object = current_member
        self.context['member'] = current_member
        return super(Preferences, self).dispatch(request)

    def form_valid(self, form):
        # E-mail changes require verification, so frig it here
        current_member = form.save(commit=False)
        new_email = current_member.email # from posted data

        # Save with original email
        current_member.email = self.orig_email
        current_member.save()

        if self.request.FILES:
            try:
                imageutils.fix_member_icon(current_member, self.request.FILES['icon'])
            except imageutils.ValidationError, e:
                self.context['image_error'] = e.args[0]
                return self.form_invalid(form)

        # E-mail change:
        if new_email != self.orig_email:
            # We check for duplicate e-mail address in change_email view,
            # so don't really need to do it here.
            send_newemail_email(current_member, new_email)
            messages.info(self.request, "To confirm the change of e-mail address, an e-mail " + \
               "has been sent to your new address with further instructions.")
        else:
            messages.info(self.request, "Changes saved.")

        # NB - AjaxyFormView not Preferences, because we want to skip the
        # behaviour of ModelFormMixin here.
        return super(AjaxyFormView, self).form_valid(form)

preferences = member_required(Preferences.as_view())


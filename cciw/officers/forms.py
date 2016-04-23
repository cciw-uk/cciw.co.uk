from datetime import date

from django import forms
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.utils import timezone

from cciw.cciwmain.models import get_reference_contact_people
from cciw.officers import create
from cciw.officers.models import Invitation, Reference
from cciw.officers.widgets import ExplicitBooleanFieldSelect
from cciw.officers.email import send_leaders_reference_email

User = get_user_model()


class StripStringsMixin(object):
    def clean(self):
        for field, value in self.cleaned_data.items():
            if isinstance(value, str):
                self.cleaned_data[field] = value.strip()
        return self.cleaned_data


class BaseForm(StripStringsMixin, forms.Form):
    pass


def fml(model, fname):
    return model._meta.get_field(fname).max_length


class CreateOfficerForm(BaseForm):
    first_name = forms.CharField()
    last_name = forms.CharField()
    email = forms.EmailField()

    def save(self):
        return create.create_officer(self.cleaned_data['first_name'],
                                     self.cleaned_data['last_name'],
                                     self.cleaned_data['email'])


class UpdateOfficerForm(BaseForm):
    first_name = forms.CharField(max_length=fml(User, 'first_name'))
    last_name = forms.CharField(max_length=fml(User, 'last_name'))
    email = forms.EmailField(max_length=fml(User, 'email'))
    notes = forms.CharField(max_length=fml(Invitation, 'notes'),
                            required=False)

    def save(self, officer_id, camp_id):
        User.objects.filter(pk=officer_id).update(
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            email=self.cleaned_data['email'])
        notes = self.cleaned_data['notes']
        Invitation.objects.filter(camp=camp_id,
                                  officer=officer_id).update(notes=notes)


class SetEmailForm(BaseForm):
    name = forms.CharField(widget=forms.TextInput(attrs={'size': '50'}))
    email = forms.EmailField(widget=forms.TextInput(attrs={'size': '50'}))

    def save(self, referee):
        referee.name = self.cleaned_data['name']
        referee.email = self.cleaned_data['email']
        referee.save()


class SendMessageForm(BaseForm):
    message = forms.CharField(widget=forms.Textarea(attrs={'cols': 80, 'rows': 20}))

    def __init__(self, *args, **kwargs):
        message_info = kwargs.pop('message_info', {})
        self.message_info = message_info
        msg_template = self.get_message_template()
        msg = render_to_string(msg_template, message_info)
        initial = kwargs.pop('initial', {})
        initial['message'] = msg
        kwargs['initial'] = initial
        return super(SendMessageForm, self).__init__(*args, **kwargs)

    def get_message_template(self):
        raise NotImplementedError


class SendReferenceRequestForm(SendMessageForm):

    def get_message_template(self):
        if self.message_info['update']:
            return 'cciw/officers/request_reference_update.txt'
        else:
            return 'cciw/officers/request_reference_new.txt'

    def clean(self):
        cleaned_data = self.cleaned_data
        url = self.message_info['url']
        if url not in cleaned_data.setdefault('message', ''):
            errmsg = "You removed the link %s from the message.  This link is needed for the referee to be able to submit their reference" % url
            self._errors.setdefault('message', self.error_class([])).append(errmsg)
            del cleaned_data['message']
        return cleaned_data


class SendNagByOfficerForm(SendMessageForm):
    def get_message_template(self):
        return 'cciw/officers/nag_by_officer_email.txt'


class CrbConsentProblemForm(SendMessageForm):
    def get_message_template(self):
        return 'cciw/officers/crb_consent_problem_email.txt'


class ReferenceForm(StripStringsMixin, forms.ModelForm):
    class Meta:
        model = Reference
        fields = ('referee_name',
                  'how_long_known',
                  'capacity_known',
                  'known_offences',
                  'known_offences_details',
                  'capability_children',
                  'character',
                  'concerns',
                  'comments')

    def __init__(self, *args, **kwargs):
        super(ReferenceForm, self).__init__(*args, **kwargs)
        reference_contact_people = get_reference_contact_people()
        if reference_contact_people:
            contact_message = (" If you would prefer to discuss your concerns on the telephone "
                               "and in confidence, please contact: " +
                               " or ".join("{0} on {1}".format(person.name,
                                                               person.phone_number)
                                           for person in reference_contact_people))
            self.fields['concerns'].label += contact_message

    def save(self, referee, user=None):
        obj = super(ReferenceForm, self).save(commit=False)
        obj.referee = referee
        obj.date_created = date.today()
        obj.save()
        self.log_reference_received(referee, user=user)
        self.send_emails(obj)

    def log_reference_received(self, referee, user=None):
        referee.log_reference_received(timezone.now())

    def send_emails(self, reference):
        send_leaders_reference_email(reference)


class AdminReferenceForm(ReferenceForm):
    def log_reference_received(self, referee, user=None):
        referee.log_reference_filled_in(user, timezone.now())


normal_textarea = forms.Textarea(attrs={'cols': 80, 'rows': 10})
small_textarea = forms.Textarea(attrs={'cols': 80, 'rows': 5})


def fix_ref_form(form_class):
    form_class.base_fields['capacity_known'].widget = small_textarea
    form_class.base_fields['known_offences'].widget = ExplicitBooleanFieldSelect()
    form_class.base_fields['known_offences_details'].widget = normal_textarea
    form_class.base_fields['capability_children'].widget = normal_textarea
    form_class.base_fields['character'].widget = normal_textarea
    form_class.base_fields['concerns'].widget = normal_textarea
    form_class.base_fields['comments'].widget = normal_textarea


fix_ref_form(ReferenceForm)
fix_ref_form(AdminReferenceForm)

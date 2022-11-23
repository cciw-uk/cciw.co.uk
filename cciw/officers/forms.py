from datetime import date

from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.forms.models import ModelForm
from django.template.loader import render_to_string
from django.utils import timezone

from cciw.accounts.models import User, get_reference_contact_users
from cciw.officers import create
from cciw.officers.email import send_leaders_reference_email
from cciw.officers.models import CampRole, Invitation, Reference
from cciw.officers.widgets import ExplicitBooleanFieldSelect


class StripStringsMixin:
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
        return create.create_officer(
            self.cleaned_data["first_name"], self.cleaned_data["last_name"], self.cleaned_data["email"]
        )

    def check_duplicates(self) -> tuple[str, bool, list[User]]:
        duplicate_message, allow_confirm, existing_users = "", True, []

        same_name_users = User.objects.filter(
            first_name__iexact=self.cleaned_data["first_name"], last_name__iexact=self.cleaned_data["last_name"]
        )
        same_email_users = User.objects.filter(email__iexact=self.cleaned_data["email"])
        same_user = same_name_users & same_email_users
        if same_user.exists():
            allow_confirm = False
            duplicate_message = "A user with that name and email address already exists. You can change the details above and try again."
        elif len(same_name_users) > 0:
            existing_users = same_name_users
            if len(existing_users) == 1:
                duplicate_message = "A user with that first name and last name " + "already exists:"
            else:
                duplicate_message = f"{len(existing_users)} users with that first name and last name already exist:"
        elif len(same_email_users):
            existing_users = same_email_users
            if len(existing_users) == 1:
                duplicate_message = "A user with that email address already exists:"
            else:
                duplicate_message = f"{len(existing_users)} users with that email address already exist:"
        return duplicate_message, allow_confirm, existing_users


class UpdateOfficerForm(ModelForm):
    role = forms.ModelChoiceField(queryset=CampRole.objects.all(), required=True)

    class Meta:
        # Based on User because we have just one field from Invitation
        model = User
        fields = ["first_name", "last_name", "email", "role"]

    def __init__(self, *args, invitation: Invitation, **kwargs):
        self.invitation = invitation
        initial = {"role": invitation.role}
        super().__init__(*args, initial=initial, **kwargs)

    def save(self, **kwargs):
        user: User = self.instance
        user.save(update_fields=["first_name", "last_name", "email"])
        role = self.cleaned_data["role"]
        self.invitation.role = role
        self.invitation.save()


class SetEmailForm(BaseForm):
    name = forms.CharField(widget=forms.TextInput(attrs={"size": "50"}))
    email = forms.EmailField(widget=forms.TextInput(attrs={"size": "50"}), required=False)

    def save(self, referee):
        referee.name = self.cleaned_data["name"]
        referee.email = self.cleaned_data["email"]
        referee.save()


class SendMessageForm(BaseForm):
    message = forms.CharField(widget=forms.Textarea(attrs={"cols": 80, "rows": 20}))

    def __init__(self, *args, **kwargs):
        message_info = kwargs.pop("message_info", {})
        self.message_info = message_info
        msg_template = self.get_message_template()
        msg = render_to_string(msg_template, message_info)
        initial = kwargs.pop("initial", {})
        initial["message"] = msg
        kwargs["initial"] = initial
        super().__init__(*args, **kwargs)

    def get_message_template(self):
        raise NotImplementedError


class SendReferenceRequestForm(SendMessageForm):
    def get_message_template(self):
        if self.message_info["update"]:
            return "cciw/officers/request_reference_update.txt"
        else:
            return "cciw/officers/request_reference_new.txt"

    def clean(self):
        cleaned_data = self.cleaned_data
        url = self.message_info["url"]
        if url not in cleaned_data.setdefault("message", ""):
            errmsg = f"You removed the link {url} from the message.  This link is needed for the referee to be able to submit their reference"
            self._errors.setdefault("message", self.error_class([])).append(errmsg)
            del cleaned_data["message"]
        return cleaned_data


class SendNagByOfficerForm(SendMessageForm):
    def get_message_template(self):
        return "cciw/officers/nag_by_officer_email.txt"


class DbsConsentProblemForm(SendMessageForm):
    def get_message_template(self):
        return "cciw/officers/dbs_consent_alert_leaders_email.txt"


class RequestDbsFormForm(SendMessageForm):
    def get_message_template(self):
        return "cciw/officers/request_dbs_form_email.txt"


class ReferenceForm(StripStringsMixin, forms.ModelForm):
    class Meta:
        model = Reference
        fields = (
            "referee_name",
            "how_long_known",
            "capacity_known",
            "known_offences",
            "known_offences_details",
            "capability_children",
            "character",
            "concerns",
            "comments",
            "given_in_confidence",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reference_contact_users = get_reference_contact_users()
        if reference_contact_users:
            contact_message = (
                " If you would prefer to discuss your concerns on the telephone "
                "and in confidence, please contact: "
                + " or ".join(f"{user.full_name} on {user.contact_phone_number}" for user in reference_contact_users)
            )
            self.fields["concerns"].label += contact_message

    def save(self, referee, user=None):
        obj = super().save(commit=False)
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


normal_textarea = forms.Textarea(attrs={"cols": 40, "rows": 10})
small_textarea = forms.Textarea(attrs={"cols": 40, "rows": 5})


def fix_ref_form(form_class):
    form_class.base_fields["capacity_known"].widget = small_textarea
    form_class.base_fields["known_offences"].widget = ExplicitBooleanFieldSelect()
    form_class.base_fields["known_offences_details"].widget = normal_textarea
    form_class.base_fields["capability_children"].widget = normal_textarea
    form_class.base_fields["character"].widget = normal_textarea
    form_class.base_fields["concerns"].widget = normal_textarea
    form_class.base_fields["comments"].widget = normal_textarea


fix_ref_form(ReferenceForm)
fix_ref_form(AdminReferenceForm)


class CciwPasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        # Unlike base class, we allow users who have never set a password to
        # reset their password, otherwise our onboarding process (which involves
        # accounts being created by someone else) can get stuck.
        return User._default_manager.filter(email__iexact=email, is_active=True)

from django.contrib import admin, messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.urls import reverse
from furl import furl

from cciw.utils.views import get_redirect_from_request


class CciwAdminSite(admin.AdminSite):
    site_header = "CCiW site administration"

    # Override both password_change and password_change_done to add our next/redirect behaviour.
    # Also disable nav sidebar
    def password_change(self, request, extra_context=None):
        """
        Handle the "change password" task -- both form display and validation.
        """
        from django.contrib.admin.forms import AdminPasswordChangeForm
        from django.contrib.auth.views import PasswordChangeView

        url = furl(reverse("admin:password_change_done", current_app=self.name))
        next_url = request.GET.get(REDIRECT_FIELD_NAME, "")
        if next_url:
            url.args[REDIRECT_FIELD_NAME] = next_url
        defaults = {
            "form_class": AdminPasswordChangeForm,
            "success_url": url.url,
            "extra_context": {**self.each_context(request), **(extra_context or {})},
        }
        defaults["extra_context"]["is_nav_sidebar_enabled"] = False
        if self.password_change_template is not None:
            defaults["template_name"] = self.password_change_template
        request.current_app = self.name
        return PasswordChangeView.as_view(**defaults)(request)

    def password_change_done(self, request, extra_context=None):
        redirect_resp = get_redirect_from_request(request)
        if redirect_resp:
            messages.info(request, "Your password has been changed.")
            return redirect_resp

        return super().password_change_done(request, extra_context=extra_context)

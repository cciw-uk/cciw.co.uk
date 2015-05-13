import autocomplete_light
from django.contrib.auth import get_user_model

import cciw.auth

User = get_user_model()


class UserAutocomplete(autocomplete_light.AutocompleteModelBase):
    search_fields = ['^first_name', '^last_name']

    def choice_label(self, user):
        return "%s %s <%s>" % (user.first_name, user.last_name, user.email)

    def choices_for_request(self):
        request = self.request
        self.choices = self.choices.order_by('first_name', 'last_name', 'email')
        if request.user.is_authenticated() and cciw.auth.is_camp_admin(request.user):
            return super(UserAutocomplete, self).choices_for_request()
        else:
            return []

autocomplete_light.register(User, UserAutocomplete, name='user')

from autocomplete_light import shortcuts as autocomplete_light

import cciw.auth
from cciw.bookings.models import BookingAccount


class BookingAccountAutocomplete(autocomplete_light.AutocompleteModelBase):
    search_fields = ['name']

    def choices_for_request(self):
        request = self.request
        self.choices = self.choices.order_by('name', 'address_post_code')
        if request.user.is_authenticated and cciw.auth.is_booking_secretary(request.user):
            return super(BookingAccountAutocomplete, self).choices_for_request()
        else:
            return []


autocomplete_light.register(BookingAccount, BookingAccountAutocomplete, name='account')

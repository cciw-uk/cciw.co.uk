from cciw.bookings.models import Price, BookingAccount, Booking, Payment, ChequePayment, RefundPayment
from anonymizer import Anonymizer

class BookingAccountAnonymizer(Anonymizer):

    model = BookingAccount

    attributes = [
        # Skipping field id
        ('email', "email"),
        ('name', "name"),
        ('address', "full_address"),
        ('post_code', "uk_postcode"),
        ('phone_number', "phonenumber"),
        ('share_phone_number', "bool"),
        #('total_received', "decimal"),
        #('first_login', "datetime"),
        #('last_login', "datetime"),
    ]


class BookingAnonymizer(Anonymizer):

    model = Booking

    attributes = [
         # Skipping field id
         # Skipping field account_id
         # Skipping field camp_id
        ('first_name', "first_name"),
        ('last_name', "last_name"),
        ('sex', "choice"),
        ('date_of_birth', "date"),
        ('address', "full_address"),
        ('post_code', "uk_postcode"),
        ('phone_number', "phonenumber"),
        ('email', "email"),
        ('church', "similar_lorem"),
        #('south_wales_transport', "bool"),
        ('contact_address', "address"),
        ('contact_post_code', "post_code"),
        ('contact_phone_number', "phonenumber"),
        ('dietary_requirements', "similar_lorem"),
        ('gp_name', "name"),
        ('gp_address', "full_address"),
        ('gp_phone_number', "phonenumber"),
        ('medical_card_number', lambda anon, obj, field, val: anon.faker.simple_pattern('####???##', field=field)),
        ('last_tetanus_injection', "date"),
        ('allergies', "similar_lorem"),
        ('regular_medication_required', "similar_lorem"),
        ('illnesses', "similar_lorem"),
        ('learning_difficulties', "similar_lorem"),
        ('serious_illness', "bool"),
        #('agreement', "bool"),
        #('price_type', "choice"),
        #('amount_due', "decimal"),
        #('shelved', "bool"),
        #('state', "choice"),
        #('created', "datetime"),
        #('booking_expires', "datetime"),
    ]


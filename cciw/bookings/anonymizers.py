from cciw.bookings.models import Price, BookingAccount, Booking, Payment, ChequePayment, RefundPayment
from anonymizer import Anonymizer

class BookingAccountAnonymizer(Anonymizer):

    model = BookingAccount

    attributes = [
        ('id', "SKIP"),
        ('email', "email"),
        ('name', "name"),
        ('address', "full_address"),
        ('post_code', "uk_postcode"),
        ('phone_number', "phonenumber"),
        ('share_phone_number', "bool"),
        ('total_received', "SKIP"),
        ('first_login', "datetime"),
        ('last_login', "SKIP"),
        ('email_communication', "SKIP")
    ]


class BookingAnonymizer(Anonymizer):

    model = Booking

    attributes = [
        ('id', "SKIP"),
        ('camp_id', "SKIP"),
        ('account_id', "SKIP"),
        ('first_name', "first_name"),
        ('last_name', "last_name"),
        ('sex', "choice"),
        ('date_of_birth', "date"),
        ('address', "full_address"),
        ('post_code', "uk_postcode"),
        ('phone_number', "phonenumber"),
        ('email', "email"),
        ('church', "similar_lorem"),
        ('south_wales_transport', "SKIP"),
        ('contact_address', "full_address"),
        ('contact_post_code', "uk_postcode"),
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
        ('agreement', "SKIP"),
        ('price_type', "SKIP"),
        ('amount_due', "SKIP"),
        ('shelved', "SKIP"),
        ('state', "SKIP"),
        ('created', "SKIP"),
        ('booking_expires', "SKIP"),
    ]


from datetime import datetime
import random

from anonymizer import Anonymizer
from cciw.officers.models import Application
from django.contrib.auth.models import User

class UserAnonymizer(Anonymizer):

    model = User

    attributes = {
        'username':   'username',
        'first_name': 'first_name',
        'last_name':  'last_name',
        'email':      'email',
        # Set the date_joined to a similar time to when they actually joined,
        # by passing the 'val' paramater
        'date_joined': lambda self, obj, field, val: self.faker.datetime(field=field, val=val),
        # Set to today:
        'last_login': lambda *args: datetime.now(),
    }

    def alter_object(self, obj):
        if obj.is_superuser:
            return False # don't change, so we can still log in.
        super(UserAnonymizer, self).alter_object(obj)
        # Destroy all passwords for everyone else
        obj.set_unusable_password()

class ApplicationAnonymizer(Anonymizer):

    model = Application

    attributes = {
        # full_name - get from officer, below
        'birth_date': lambda self, obj, field, val: self.faker.date(field=field, val=val),
        'birth_place': 'city',
        'address_firstline': 'street_address',
        'address_town': 'city',
        'address_county': 'uk_county',
        'address_postcode': 'uk_postcode',
        'address_country': 'uk_country',
        'address_tel': 'phonenumber',
        'address_mobile': 'phonenumber',
        'address_email': 'email',

        'address2_address': 'full_address',
        'address3_address': 'full_address',

        'christian_experience': 'lorem',
        'youth_experience': 'lorem',

        'youth_work_declined': 'bool',
        'youth_work_declined_details': lambda *args: "",

        'crime_declaration': 'bool',
        'court_declaration': 'bool',
        'concern_declaration': 'bool',
        'allegation_declaration': 'bool',
        'crime_details': lambda self, obj, field, val: "",
        'court_details': lambda self, obj, field, val: "",
        'concern_details': lambda self, obj, field, val: "",
        }

    order = 2

    def alter_object(self, obj):
        super(ApplicationAnonymizer, self).alter_object(obj)
        obj.full_name = "%s %s" % (obj.officer.first_name, obj.officer.last_name)
        obj.full_maiden_name = obj.full_name

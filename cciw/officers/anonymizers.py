from datetime import datetime

from anonymizer import Anonymizer
from cciw.officers.models import Application, ReferenceForm
from django.contrib.auth.models import User

class UserAnonymizer(Anonymizer):

    order = 1

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


yyyymmpattern = lambda self, obj, field, val: self.faker.simple_pattern("####/##", field=field)

class ApplicationAnonymizer(Anonymizer):

    model = Application

    attributes = {
        # 'full_name': "name", - see below
        #'full_maiden_name': "name",
        'birth_date': "date",
        'birth_place': "city",
        'address_firstline': "street_address",
        'address_town': "city",
        'address_county': "uk_county",
        'address_postcode': "uk_postcode",
        'address_country': "uk_country",
        'address_tel': "phonenumber",
        'address_mobile': "phonenumber",
        'address_email': "email",
        'address_since': yyyymmpattern,
        'address2_from': yyyymmpattern,
        'address2_to': yyyymmpattern,
        'address2_address': "full_address",
        'address3_from': yyyymmpattern,
        'address3_to': yyyymmpattern,
        'address3_address': "full_address",
        'christian_experience': "lorem",
        'youth_experience': "lorem",
        'youth_work_declined': "bool",
        'youth_work_declined_details': "lorem",
        'relevant_illness': "bool",
        'illness_details': "lorem",
        'employer1_name': "company",
        'employer1_from': yyyymmpattern,
        'employer1_to': yyyymmpattern,
        'employer1_job': lambda self, obj, field, val: self.faker.varchar(60, field=field),
        'employer1_leaving': lambda self, obj, field, val: self.faker.varchar(150, field=field),
        'employer2_name': "company",
        'employer2_from': yyyymmpattern,
        'employer2_to': yyyymmpattern,
        'employer2_job': lambda self, obj, field, val: self.faker.varchar(60, field=field),
        'employer2_leaving': lambda self, obj, field, val: self.faker.varchar(150, field=field),
        'referee1_name': "name",
        'referee1_address': "full_address",
        'referee1_tel': "phonenumber",
        'referee1_mobile': "phonenumber",
        'referee1_email': "email",
        'referee2_name': "name",
        'referee2_address': "full_address",
        'referee2_tel': "phonenumber",
        'referee2_mobile': "phonenumber",
        'referee2_email': "email",
        'crime_declaration': "bool",
        'crime_details': "lorem",
        'court_declaration': "bool",
        'court_details': "lorem",
        'concern_declaration': "bool",
        'concern_details': "lorem",
        'allegation_declaration': "bool",
        'crb_check_consent': "bool",
        # 'finished': "bool", - leave as is
        'date_submitted': "date",
    }

    order = 2

    def alter_object(self, obj):
        super(ApplicationAnonymizer, self).alter_object(obj)
        obj.full_name = "%s %s" % (obj.officer.first_name, obj.officer.last_name)
        obj.full_maiden_name = obj.full_name


class ReferenceFormAnonymizer(Anonymizer):

    model = ReferenceForm

    attributes = {
        'referee_name': "name",
        'how_long_known': lambda self, obj, field, val: self.faker.varchar(150, field=field),
        'capacity_known': "lorem",
        'known_offences': "bool",
        'known_offences_details': "lorem",
        'capability_children': "lorem",
        'character': "lorem",
        'concerns': "lorem",
        'comments': "lorem",
        # 'date_created': "date",
    }
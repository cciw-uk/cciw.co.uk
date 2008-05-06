from django.db import models
from django import oldforms as forms
from django.dispatch import dispatcher
from django.core.validators import ValidationError
from django.http import HttpResponseForbidden
from django.db.models.options import AdminOptions

from cciw.cciwmain.models import Camp
from cciw.officers import signals
from django.contrib.auth.models import User
import cciw.middleware.threadlocals as threadlocals
import re
import datetime

yyyy_mm_re = re.compile('^\d{4}/\d{2}$')

def rqd_field_validator(field_data, all_data):
    if all_data.get('finished', 'off') == 'on':
        if len(field_data) == 0:
            raise ValidationError("This is a required field.")
rqd_field_validator.always_test = True

def rqd_null_boolean_validator(field_data, all_data):
    if all_data.get('finished', 'off') == 'on':
        if field_data == '' or field_data == '1':
            raise ValidationError("This is a required field.")
rqd_null_boolean_validator.always_test = True

def required_field(field_class, *args, **kwargs):
    """Returns a field with options set appropiately
    for Application required fields - i.e., they are
    allowed to be blank but if 'finished' is true
    then they must be filled in."""
    kwargs['blank'] = True
    validators = list(kwargs.get('validator_list', ()))
    if field_class is ExplicitBooleanField:
        validators.append(rqd_null_boolean_validator)
    else:
        validators.append(rqd_field_validator)
    kwargs['validator_list'] = validators
    return field_class(*args, **kwargs)
    
def yyyy_mm_validator(field_data, all_data):
    if not yyyy_mm_re.match(field_data):
        raise ValidationError("This field must be in the form YYYY/MM.")

# Pretend class (it's easier to avoid some ORM magic this way)
def YyyyMmField(*args, **kwargs):
    kwargs['max_length'] = 7
    validators = list(kwargs.get('validator_list', ()))
    validators.append(yyyy_mm_validator)
    kwargs['validator_list'] = validators
    kwargs['help_text'] = u'Enter the date in YYYY/MM format.'
    return models.CharField(*args, **kwargs)

def AddressField(*args, **kwargs):
    kwargs['help_text'] = u'Full address, including post code and country'
    return models.TextField(*args, **kwargs)

class ExplicitBooleanField(models.NullBooleanField):
    def __init__(self, *args, **kwargs):
        kwargs['radio_admin'] = True
        kwargs['default'] = None
        models.NullBooleanField.__init__(self, *args, **kwargs)

    def get_manipulator_field_objs(self):
        return [FormsExplicitBooleanField]

class FormsExplicitBooleanField(forms.RadioSelectField):
    """This FormsExplicitBooleanField provides 'Yes', 'No' and 'Unknown', 
    mapping results to True, False or None"""
    def __init__(self, field_name, is_required=False, validator_list=[]):
        forms.RadioSelectField.__init__(self, field_name, choices=[('2', 'Yes'), ('3', 'No')],
            is_required=is_required, validator_list=validator_list, ul_class='radiolist inline')

    def render(self, data):
        if data is None: data = '1'
        elif data == True: data = '2'
        elif data == False: data = '3'
        return forms.RadioSelectField.render(self, data)

    @staticmethod
    def html2python(data):
        return {'1': None, '2': True, '3': False}.get(data, None)

if not threadlocals.is_web_request():
    # When installing, we need the following line.  It is only
    # executed in the command line context.
    ExplicitBooleanField = models.NullBooleanField

class Application(models.Model):
    camp = models.ForeignKey(Camp, null=True, limit_choices_to={'online_applications': True})
    officer = models.ForeignKey(User, blank=True) # blank=True to get the admin to work
    full_name = required_field(models.CharField, 'full name', max_length=60)
    full_maiden_name = models.CharField('full maiden name', max_length=60, blank=True)
    birth_date = required_field(models.DateField, 'date of birth', null=True, default=None)
    birth_place = required_field(models.CharField, 'place of birth', max_length=60)
    address_firstline = required_field(models.CharField, 'address', max_length=40)
    address_town = required_field(models.CharField, 'town/city', max_length=60) # 60 == len("Llanfairpwllgwyngyllgogerychwyrndrobwyll-llantysiliogogogoch")
    address_county = required_field(models.CharField, 'county', max_length=30)
    address_postcode = required_field(models.CharField, 'post code', max_length=10)
    address_country = required_field(models.CharField, 'country', max_length=30)
    address_tel = required_field(models.CharField, 'telephone', max_length=22, blank=True) # +44-(0)1224-XXXX-XXXX
    address_mobile = models.CharField('mobile', max_length=22, blank=True)
    address_email = required_field(models.EmailField, 'e-mail')
    address_since = required_field(YyyyMmField, 'resident at address since')

    address2_from = YyyyMmField('resident at address from', blank=True)
    address2_to = YyyyMmField('resident at address until', blank=True)
    address2_address = AddressField('address', blank=True)

    address3_from = YyyyMmField('resident at address from', blank=True)
    address3_to = YyyyMmField('resident at address until', blank=True)
    address3_address = AddressField('address', blank=True)

    christian_experience = required_field(models.TextField, 'christian experience')
    youth_experience = required_field(models.TextField, 'youth work experience')
    
    youth_work_declined = required_field(ExplicitBooleanField, 'Have you ever had an offer to work with children/young people declined?')
    youth_work_declined_details = models.TextField('details', blank=True)
    
    relevant_illness = required_field(ExplicitBooleanField, '''Do you suffer or have you suffered from any
            illness which may directly affect your work with children/young people?''')
    illness_details = models.TextField('illness details', blank=True)
    
    employer1_name = models.CharField("1. Employer's name and address", max_length=100, blank=True)
    employer1_from = YyyyMmField("Employed from", blank=True)
    employer1_to = YyyyMmField("Employed until", blank=True)
    employer1_job = models.CharField("Job description", max_length=60, blank=True)
    employer1_leaving = models.CharField("Reason for leaving", max_length=150, blank=True)
    
    employer2_name = models.CharField("2. Employer's name and address", max_length=100, blank=True)
    employer2_from = YyyyMmField("Employed from", blank=True)
    employer2_to = YyyyMmField("Employed until", blank=True)
    employer2_job = models.CharField("Job description", max_length=60, blank=True)
    employer2_leaving = models.CharField("Reason for leaving", max_length=150, blank=True)
    
    referee1_name = required_field(models.CharField, "First referee's name", max_length=60)
    referee1_address = required_field(AddressField, 'address')
    referee1_tel = models.CharField('telephone', max_length=22, blank=True) # +44-(0)1224-XXXX-XXXX
    referee1_mobile = models.CharField('mobile', max_length=22, blank=True)
    referee1_email = models.EmailField('e-mail', blank=True)

    referee2_name = required_field(models.CharField, "Second referee's name", max_length=60)
    referee2_address = required_field(AddressField, 'address')
    referee2_tel = models.CharField('telephone', max_length=22, blank=True) # +44-(0)1224-XXXX-XXXX
    referee2_mobile = models.CharField('mobile', max_length=22, blank=True)
    referee2_email = models.EmailField('e-mail', blank=True)
    
    crime_declaration = required_field(ExplicitBooleanField, 
            """Have you ever been charged with or convicted
            of a criminal offence or are the subject of criminal 
            proceedings?""")
    crime_details = models.TextField("If yes, give details", blank=True)

    court_declaration = required_field(ExplicitBooleanField, 
        '''Have you ever been involved in Court 
           proceedings concerning a child for whom you have 
           parental responsibility?''')
    court_details = models.TextField("If yes, give details", blank=True)

    concern_declaration = required_field(ExplicitBooleanField, 
            """Has there ever been any cause for concern 
               regarding your conduct with children/young people?""")
    concern_details = models.TextField("If yes, give details", blank=True)

    allegation_declaration = required_field(ExplicitBooleanField, 
            """To your knowledge have you ever had any 
            allegation made against you concerning children/young people 
            which has been reported to and investigated by Social 
            Services and /or the Police?""")

    crb_check_consent = required_field(ExplicitBooleanField, 
            """Do you consent to the obtaining of a Criminal
            Records Bureau check on yourself? """)
    
    finished = models.BooleanField("is the above information complete?", default=False)
    
    date_submitted = models.DateField('date submitted', null=True, blank=True)
    
    def save(self):
        if not hasattr(self, 'officer_id') or self.officer_id is None:
            self.officer_id = threadlocals.get_current_user().id
        self.date_submitted = datetime.date.today()
        super(Application, self).save()
        dispatcher.send(signals.application_saved, sender=self, application=self)

    def __unicode__(self):
        if self.camp is not None:
            return u"Application from %s, %d, camp %d" % (self.full_name, self.camp.year, self.camp.number)
        else:
            return u"Application from %s" % self.full_name

    class Meta:
        ordering = ('-camp__year', 'officer__first_name', 'officer__last_name', 'camp__number')
        
    class Admin:
        fields = () # we override this later

        save_as = True
        list_display = ('full_name', 'officer', 'camp', 'finished', 'date_submitted')
        list_filter = ('finished','date_submitted')
        ordering = ('full_name',)
        search_fields = ('full_name',)

camp_officer_application_fields = (
    (None,
        {'fields': ('camp', ),
          'classes': 'wide',}
    ),
    ('Personal info', 
        {'fields': ('full_name', 'full_maiden_name', 'birth_date', 'birth_place'),
         'classes': 'applicationpersonal wide'}
    ),
    ('Address', 
        {'fields': ('address_firstline', 'address_town', 'address_county',
                    'address_postcode', 'address_country', 'address_tel',
                    'address_mobile', 'address_since', 'address_email'),
         'classes': 'wide',}
    ),
    ('Previous addresses',
        {'fields': ('address2_from', 'address2_to', 'address2_address'),
         'classes': 'wide',
         'description': """If you have lived at your current address for less than 5 years
                        please give previous address(es) with dates below. (If more than 2 addresses,
                        use the second address box for the remaining addresses with their dates)"""}
    ),
    (None,
        {'fields': ('address3_from', 'address3_to', 'address3_address'),
         'classes': 'wide',}
    ),
    ('Experience',
        {'fields': ('christian_experience',),
         'classes': 'wide',
         'description': '''Please tells us about your Christian experience 
            (i.e. how you became a Christian and how long you have been a Christian, 
            which Churches you have attended and dates, names of minister/leader)'''}
            
    ),
    (None,
        {'fields': ('youth_experience',),
         'classes': 'wide',
         'description': '''Please give details of previous experience of
            looking after or working with children/young people - 
            include any qualifications or training you have. '''}
    ),
    (None,
        {'fields': ('youth_work_declined', 'youth_work_declined_details'),
         'classes': 'wide',
         'description': 'If you have ever had an offer to work with children/young people declined, you must declare it below and give details.'}
    ),
    ('Illnesses',
        {'fields': ('relevant_illness', 'illness_details'),
         'classes': 'wide' }
    ),
    ('Employment history',
        {'fields': ('employer1_name', 'employer1_from', 'employer1_to', 
                    'employer1_job', 'employer1_leaving', 'employer2_name', 
                    'employer2_from', 'employer2_to', 'employer2_job', 
                    'employer2_leaving',),
         'classes': 'wide',
          'description': 'Please tell us about your past and current employers below (if applicable)'}
    ),
    ('References',
        {'fields': ('referee1_name', 'referee1_address', 'referee1_tel', 'referee1_mobile', 'referee1_email',
                    'referee2_name', 'referee2_address', 'referee2_tel', 'referee2_mobile', 'referee2_email',),
         'classes': 'wide',
         'description': '''Please give the names and addresses, 
            telephones numbers and e-mail addresses and role or 
            relationship of <strong>two</strong> people who know you 
            well and who would be able to give a personal character reference.
            In addition we reserve the right to take up additional character 
            references from any other individuals deemed necessary. <strong>One 
            reference must be from a Church leader. The other reference should 
            be from someone who has known you for more than 5 years.</strong>'''}
    ),
    ('Declarations (see note below)',
        {'fields': ('crime_declaration', 'crime_details'),
         'classes': 'wide',
         'description': '''Note: The disclosure of an offence may not 
            prohibit your appointment'''},
    ),
    (None,
        {'fields': ('court_declaration', 'court_details'),
         'classes': 'wide', }
    ),
    (None,
        {'fields': ('concern_declaration', 'concern_details'),
         'classes': 'wide' }
    ),
    (None,
        {'fields': ('allegation_declaration',),
         'classes': 'wide',
         'description': '''If you answer yes to the following question
            we will need to discuss this with you''' }
    ),            
    (None,
        {'fields': ('crb_check_consent',),
         'classes': 'wide',
         'description': '''If you answer NO  to
            the following question we regret that we 
            cannot proceed with your application. ''' }
    ),
    ("Confirmation",
        {'fields': ('finished',),
         'classes': 'wide',
         'description': """By ticking this box and pressing save, you confirm 
         that the information you have submitted is correct and complete, and your
         information will then be sent to the camp leader.  By leaving this box un-ticked,
         you can save what you have done so far and edit it later."""
         }
    ),
)

camp_leader_application_fields = (
    (None, 
        {'fields': ('officer',), 
          'classes': 'wide',}
    ),) + camp_officer_application_fields

class ApplicationAdminOptions(AdminOptions):
    """Class used to replace AdminOptions for the Application model"""
    def _fields(self):
        user = threadlocals.get_current_user()
        if user is None or user.is_anonymous():
            # never get here normally
            return ()
        else:
            if user.has_perm('officers.change_application'):
                return camp_leader_application_fields
            else:
                return camp_officer_application_fields
    fields = property(_fields)

# HACK
# The inner 'Admin' class has been transformed into Application._meta.admin 
# by this point, due to metaclass magic. We can alter it's behaviour like this:
del Application._meta.admin.fields
Application._meta.admin.__class__ = ApplicationAdminOptions


class Reference(models.Model):
    application = models.ForeignKey(Application, limit_choices_to={'finished': True})
    referee_number = models.SmallIntegerField("Referee number", choices=((1,'1'), (2,'2')))
    requested = models.BooleanField()
    received = models.BooleanField()
    comments = models.TextField(blank=True)

    def __unicode__(self):
        app = self.application
        # Due to this being called before object is saved to the 
        # database in admin, self.referee_number can sometimes be a string
        refnum = int(self.referee_number)
        
        if refnum not in (1,2):
            return u"<Reference improperly created>"
        referee_name = getattr(app, "referee%d_name" % refnum)
        return u"For %s %s | From %s | Camp %d, %d" % (app.officer.first_name, 
                                                       app.officer.last_name, 
                                                       referee_name, 
                                                       app.camp.number,
                                                       app.camp.year)

    class Meta:
        ordering = ('application__camp__year', 
                    'application__officer__first_name', 
                    'application__officer__last_name',
                    'application__camp__number',
                    'referee_number')
        unique_together = (("application", "referee_number"),)

    class Admin:
        search_fields = ['application__officer__first_name', 'application__officer__last_name']

class Invitation(models.Model):
    officer = models.ForeignKey(User)
    camp = models.ForeignKey(Camp)

    class Meta:
        ordering = ('-camp__year', 'officer__first_name', 'officer__last_name')
        unique_together = (('officer', 'camp'),)

    class Admin:
        pass


# Ensure hooks get set up
import cciw.officers.hooks

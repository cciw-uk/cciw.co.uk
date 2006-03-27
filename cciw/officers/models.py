from django.db import models
from django.core.validators import ValidationError
from django.http import HttpResponseForbidden
from django.db.models.options import AdminOptions

from cciw.cciwmain.models import Camp
from django.contrib.auth.models import User
import cciw.middleware.threadlocals as threadlocals
import re
import datetime

yyyy_mm_re = re.compile('^\d{4}/\d{2}$')

def assert_ticked(field_data, all_data):
    raise ValidationError("value " + field_data + " is not allowed")

def yyyy_mm_validator(field_data, all_data):
    if not yyyy_mm_re.match(field_data):
        raise ValidationError("This field must be in the form YYYY-MM.")

# Pretend class (it's easier to avoid some ORM magic this way)
def YyyyMmField(*args, **kwargs):
    kwargs['maxlength'] = 7
    kwargs['validator_list'] = [yyyy_mm_validator]
    kwargs['help_text'] = 'Enter the date in YYYY-MM format.'
    return models.CharField(*args, **kwargs)

def AddressField(*args, **kwargs):
    kwargs['help_text'] ='Full address, including post code and country'
    return models.TextField(*args, **kwargs)

YES_NO = (
    (1, 'YES'),
    (0, 'NO'),
)

def ExplicitBooleanField(*args, **kwargs):
    kwargs['choices'] = YES_NO
    kwargs['radio_admin'] = True
    return models.PositiveSmallIntegerField(*args, **kwargs)

class Application(models.Model):
    camp = models.ForeignKey(Camp, limit_choices_to={'start_date__gt': models.LazyDate()})
    officer = models.ForeignKey(User, blank=True, default=None) # null=True to get the admin to work
    full_name = models.CharField('full name', maxlength=60, blank=False)
    full_maiden_name = models.CharField('full maiden name', maxlength=60, blank=True)
    birth_date = models.DateField('date of birth')
    birth_place = models.CharField('place of birth', maxlength=60)
    address_firstline = models.CharField('address', maxlength=40)
    address_town = models.CharField('town/city', maxlength=60) # 60 == len("Llanfairpwllgwyngyllgogerychwyrndrobwyll-llantysiliogogogoch")
    address_county = models.CharField('county', maxlength=30)
    address_postcode = models.CharField('post code', maxlength=10)
    address_country = models.CharField('country', maxlength=30)
    address_tel = models.CharField('telephone', maxlength=22, blank=True) # +44-(0)1224-XXXX-XXXX
    address_mobile = models.CharField('mobile', maxlength=22, blank=True)
    address_email = models.EmailField('e-mail')
    address_since = YyyyMmField('resident at address since')

    address2_from = YyyyMmField('resident at address from', blank=True)
    address2_to = YyyyMmField('resident at address until', blank=True)
    address2_address = AddressField('address', blank=True)

    address3_from = YyyyMmField('resident at address from', blank=True)
    address3_to = YyyyMmField('resident at address until', blank=True)
    address3_address = AddressField('address', blank=True)

    christian_experience = models.TextField('christian experience')
    youth_experience = models.TextField('youth work experience')
    
    youth_work_declined = ExplicitBooleanField('Have you ever had an offer to work with children/young people declined?')
    youth_work_declined_details = models.TextField('details', blank=True)
    
    relevant_illness = ExplicitBooleanField('Any illnesses which may affect work with children?')
    illness_details = models.TextField('illness details', blank=True)
    
    employer1_name = models.CharField("1. Employer's name and address", maxlength=100, blank=True)
    employer1_from = YyyyMmField("Employed from", blank=True)
    employer1_to = YyyyMmField("Employed until", blank=True)
    employer1_job = models.CharField("Job description", maxlength=60, blank=True)
    employer1_leaving = models.CharField("Reason for leaving", maxlength=150, blank=True)
    
    employer2_name = models.CharField("2. Employer's name and address", maxlength=100, blank=True)
    employer2_from = YyyyMmField("Employed from", blank=True)
    employer2_to = YyyyMmField("Employed until", blank=True)
    employer2_job = models.CharField("Job description", maxlength=60, blank=True)
    employer2_leaving = models.CharField("Reason for leaving", maxlength=150, blank=True)
    
    referee1_name = models.CharField("First referee's name", maxlength=60)
    referee1_address = AddressField('address')
    referee1_tel = models.CharField('telephone', maxlength=22, blank=True) # +44-(0)1224-XXXX-XXXX
    referee1_mobile = models.CharField('mobile', maxlength=22, blank=True)
    referee1_email = models.EmailField('e-mail', blank=True)

    referee2_name = models.CharField("Second referee's name", maxlength=60)
    referee2_address = AddressField('address')
    referee2_tel = models.CharField('telephone', maxlength=22, blank=True) # +44-(0)1224-XXXX-XXXX
    referee2_mobile = models.CharField('mobile', maxlength=22, blank=True)
    referee2_email = models.EmailField('e-mail', blank=True)
    
    crime_declaration = ExplicitBooleanField("YES or NO")
    crime_details = models.TextField("If yes, give details", blank=True)

    court_declaration = ExplicitBooleanField("YES or NO")
    court_details = models.TextField("If yes, give details", blank=True)

    concern_declaration = ExplicitBooleanField("YES or NO")
    concern_details = models.TextField("If yes, give details", blank=True)

    allegation_declaration = ExplicitBooleanField("YES or NO")

    crb_check_consent = ExplicitBooleanField("YES or NO")
    date_submitted = models.DateField('date submitted', blank=True)
    
    def save(self):
        if not hasattr(self, 'officer_id') or self.officer_id is None:
            self.officer_id = threadlocals.get_current_user().id
        self.date_submitted = datetime.date.today()
        super(Application, self).save()
    
    def __repr__(self):
        return "Application from %s, %d" % (self.full_name, self.camp.year)

    class Meta:
        pass
        
    class Admin:
        fields = () # we override this later

        save_as = True
        list_display = ('full_name', 'officer', 'camp', 'date_submitted')

camp_officer_application_fields = (
    (None,
        {'fields': ('camp',),
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
                        please give previous address(es) with dates below."""}
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
         'classes': 'wide',
         'description':  '''Do you suffer or have you suffered from any
            illness which may directly affect your work with 
            children/young people?   If 'Yes' give details below.'''}
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
         'description': '''Have you ever been charged with or convicted
            of a criminal offence or are the subject of criminal 
            proceedings? (Note: The disclosure of an offence may not 
            prohibit your appointment)'''},
    ),
    (None,
        {'fields': ('court_declaration', 'court_details'),
         'classes': 'wide',
         'description': '''Have you ever been involved in Court 
            proceedings concerning a child for whom you have 
            parental responsibility?''' }
    ),
    (None,
        {'fields': ('concern_declaration', 'concern_details'),
         'classes': 'wide',
         'description': '''Has there ever been any cause for concern 
            regarding your conduct with children/young people?''' }
    ),
    (None,
        {'fields': ('allegation_declaration',),
         'classes': 'wide',
         'description': '''To your knowledge have you ever had any 
            allegation made against you concerning children/young people 
            which has been reported to and investigated by Social 
            Services and /or the Police?  If Yes we will need to discuss 
            this with you''' }
    ),            
    (None,
        {'fields': ('crb_check_consent',),
         'classes': 'wide',
         'description': '''Do you consent to the obtaining of a Criminal
            Records Bureau check on yourself? If NO we regret that we 
            cannot proceed with your application. ''' }
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

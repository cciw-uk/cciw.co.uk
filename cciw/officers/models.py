# -*- coding: utf-8 -*-
from django.db import models
from django.dispatch import dispatcher
from django.core.validators import ValidationError
from django.http import HttpResponseForbidden

from cciw.cciwmain.models import Camp
from cciw.officers import signals
from django.contrib.auth.models import User
import datetime
from fields import YyyyMmField, AddressField, ExplicitBooleanField, required_field

class Referee(object):
    """Helper class for more convenient access to referee* attributes
    of 'Application' model."""
    def __init__(self, appobj, refnum):
        self._appobj = appobj
        self._refnum = refnum

    def __getattr__(self, name):
        attname = "referee%d_%s" % (self._refnum, name)
        return getattr(self._appobj, attname)

    def __setattr__(self, name, val):
        if name.startswith('_'):
            self.__dict__[name] = val
        else:
            attname = "referee%d_%s" % (self._refnum, name)
            setattr(self._appobj, attname, val)

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

    # Convenience wrapper around 'referee?_*' fields:
    @property
    def referees(self):
        try:
            return self._referees_cache
        except AttributeError:
            # Use tuple since we don't want assignment or mutation to the list
            retval = tuple(Referee(self, refnum) for refnum in (1,2)) 
            self._referees_cache = retval
            return retval

    @property
    def references(self):
        """A cached version of 2 items that can exist in 'references_set', 
        but with 'None' instead of exceptions if they are not there. Read only"""
        try:
            return self._references_cache
        except AttributeError:
            retval = (self._ref(1), self._ref(2))
            self._references_cache = retval
            return retval
    
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

    def _ref(self, num):
        try:
            return self.reference_set.get(referee_number=num)
        except Reference.DoesNotExist:
            return None

    class Meta:
        ordering = ('-camp__year', 'officer__first_name', 'officer__last_name', 'camp__number')


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

class Invitation(models.Model):
    officer = models.ForeignKey(User)
    camp = models.ForeignKey(Camp)

    def __unicode__(self):
        return u"%s %s — camp %s" % (self.officer.first_name, self.officer.last_name, self.camp)
        

    class Meta:
        ordering = ('-camp__year', 'officer__first_name', 'officer__last_name')
        unique_together = (('officer', 'camp'),)

# Ensure hooks get set up
import cciw.officers.hooks

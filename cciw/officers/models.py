# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, date
import re

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from cciw.cciwmain.models import Camp
from cciw.officers.fields import YyyyMmField, AddressField, RequiredCharField, RequiredDateField, RequiredTextField, RequiredEmailField, RequiredYyyyMmField, RequiredAddressField, RequiredExplicitBooleanField


class Referee(object):
    """
    Helper class for more convenient access to referee* attributes
    of 'Application' model and referee details from 'Reference' model
    """
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

    def __eq__(self, other):
        return self.name == other.name and self.email == other.email


class ApplicationManager(models.Manager):
    use_for_related_fields = True

    def get_queryset(self):
        return super(ApplicationManager, self).get_queryset().select_related('officer')


NAME_LENGTH = 100
REFEREE_NAME_HELP_TEXT = "Name only - please do not include job title or other information."


class Application(models.Model):
    officer = models.ForeignKey(User, blank=True) # blank=True to get the admin to work
    full_name = RequiredCharField('full name', max_length=NAME_LENGTH)
    full_maiden_name = models.CharField('full maiden name', max_length=NAME_LENGTH, blank=True)
    birth_date = RequiredDateField('date of birth', null=True, default=None)
    birth_place = RequiredCharField('place of birth', max_length=60)
    address_firstline = RequiredCharField('address', max_length=40)
    address_town = RequiredCharField('town/city', max_length=60) # 60 == len("Llanfairpwllgwyngyllgogerychwyrndrobwyll-llantysiliogogogoch")
    address_county = RequiredCharField('county', max_length=30)
    address_postcode = RequiredCharField('post code', max_length=10)
    address_country = RequiredCharField('country', max_length=30)
    address_tel = RequiredCharField('telephone', max_length=22, blank=True) # +44-(0)1224-XXXX-XXXX
    address_mobile = models.CharField('mobile', max_length=22, blank=True)
    address_email = RequiredEmailField('e-mail')
    address_since = RequiredYyyyMmField('resident at address since')

    address2_from = YyyyMmField('resident at address from', blank=True)
    address2_to = YyyyMmField('resident at address until', blank=True)
    address2_address = AddressField('address', blank=True)

    address3_from = YyyyMmField('resident at address from', blank=True)
    address3_to = YyyyMmField('resident at address until', blank=True)
    address3_address = AddressField('address', blank=True)

    christian_experience = RequiredTextField('christian experience')
    youth_experience = RequiredTextField('youth work experience')

    youth_work_declined = RequiredExplicitBooleanField('Have you ever had an offer to work with children/young people declined?')
    youth_work_declined_details = models.TextField('details', blank=True)

    relevant_illness = RequiredExplicitBooleanField('''Do you suffer or have you suffered from any
            illness which may directly affect your work with children/young people?''')
    illness_details = models.TextField('illness details', blank=True)

    employer1_name = models.CharField("1. Employer's name and address", max_length=NAME_LENGTH, blank=True)
    employer1_from = YyyyMmField("Employed from", blank=True)
    employer1_to = YyyyMmField("Employed until", blank=True)
    employer1_job = models.CharField("Job description", max_length=60, blank=True)
    employer1_leaving = models.CharField("Reason for leaving", max_length=150, blank=True)

    employer2_name = models.CharField("2. Employer's name and address", max_length=NAME_LENGTH, blank=True)
    employer2_from = YyyyMmField("Employed from", blank=True)
    employer2_to = YyyyMmField("Employed until", blank=True)
    employer2_job = models.CharField("Job description", max_length=60, blank=True)
    employer2_leaving = models.CharField("Reason for leaving", max_length=150, blank=True)

    referee1_name = RequiredCharField("First referee's name", max_length=NAME_LENGTH,
                                   help_text=REFEREE_NAME_HELP_TEXT)
    referee1_address = RequiredAddressField('address')
    referee1_tel = models.CharField('telephone', max_length=22, blank=True) # +44-(0)1224-XXXX-XXXX
    referee1_mobile = models.CharField('mobile', max_length=22, blank=True)
    referee1_email = models.EmailField('e-mail', blank=True)

    referee2_name = RequiredCharField("Second referee's name", max_length=NAME_LENGTH,
                                   help_text=REFEREE_NAME_HELP_TEXT)
    referee2_address = RequiredAddressField('address')
    referee2_tel = models.CharField('telephone', max_length=22, blank=True) # +44-(0)1224-XXXX-XXXX
    referee2_mobile = models.CharField('mobile', max_length=22, blank=True)
    referee2_email = models.EmailField('e-mail', blank=True)

    crime_declaration = RequiredExplicitBooleanField(
            """Have you ever been charged with or convicted
            of a criminal offence or are the subject of criminal
            proceedings?""")
    crime_details = models.TextField("If yes, give details", blank=True)

    court_declaration = RequiredExplicitBooleanField(
        '''Have you ever been involved in Court
           proceedings concerning a child for whom you have
           parental responsibility?''')
    court_details = models.TextField("If yes, give details", blank=True)

    concern_declaration = RequiredExplicitBooleanField(
            """Has there ever been any cause for concern
               regarding your conduct with children/young people?""")
    concern_details = models.TextField("If yes, give details", blank=True)

    allegation_declaration = RequiredExplicitBooleanField(
            """To your knowledge have you ever had any
            allegation made against you concerning children/young people
            which has been reported to and investigated by Social
            Services and /or the Police?""")

    crb_check_consent = RequiredExplicitBooleanField(
            """Do you consent to the obtaining of a Criminal
            Records Bureau check on yourself? """)

    finished = models.BooleanField("is the above information complete?", default=False)

    date_submitted = models.DateField('date submitted', null=True, blank=True)

    objects = ApplicationManager()

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
        """A cached version of 2 items that can exist in 'references_set', which
        are created if they don't exist. Read only"""
        try:
            return self._references_cache
        except AttributeError:
            retval = (self._ref(1), self._ref(2))
            self._references_cache = retval
            return retval

    @property
    def one_line_address(self):
        return ", ".join(filter(bool, [self.address_firstline,
                                       self.address_town,
                                       self.address_county,
                                       self.address_postcode,
                                       self.address_country]))

    def __str__(self):
        if self.date_submitted is not None:
            submitted = "submitted " + self.date_submitted.strftime("%Y-%m-%d")
        else:
            submitted = "incomplete"
        return "Application from %s (%s)" % (self.full_name, submitted)

    def _ref(self, num):
        return self.reference_set.get_or_create(referee_number=num)[0]

    class Meta:
        ordering = ('-date_submitted', 'officer__first_name', 'officer__last_name',)

    def could_be_for_camp(self, camp):
        # An application is 'for' a camp if it is submitted in the year before
        # the camp start date. Logic duplicated in applications_for_camp
        return (self.date_submitted <= camp.start_date and
                self.date_submitted > camp.start_date - timedelta(days=365))


class ReferenceManager(models.Manager):
    # manager to reduce number of SQL queries, especially in admin
    use_for_related_fields = True
    def get_queryset(self):
        return super(ReferenceManager, self).get_queryset().select_related('application__officer')


class Reference(models.Model):
    """
    Stores metadata about a reference for an officer.
    """
    # The actual reference is stored in ReferenceForm model.  This should have
    # been named ReferenceMeta or something.
    application = models.ForeignKey(Application, limit_choices_to={'finished': True})
    referee_number = models.SmallIntegerField("Referee number", choices=((1,'1'), (2,'2')))
    requested = models.BooleanField(default=False)
    received = models.BooleanField(default=False)
    comments = models.TextField(blank=True)

    objects = ReferenceManager()

    def __str__(self):
        app = self.application
        # Due to this being called before object is saved to the
        # database in admin, self.referee_number can sometimes be a string
        refnum = int(self.referee_number)

        if refnum not in (1,2):
            return "<Reference improperly created>"
        referee_name = app.referees[refnum - 1].name
        return "For %s %s | From %s | %s" % (app.officer.first_name,
                                              app.officer.last_name,
                                              referee_name,
                                              app.date_submitted.strftime('%Y-%m-%d'))

    @property
    def referee(self):
        return Referee(self.application, self.referee_number)

    @property
    def reference_form(self):
        """
        Returns the actual reference form data, or None if not available
        """
        # A simple wrapper around the OneToOne reverse relation, turning
        # 'DoesNotExist' into 'None'
        try:
            return self._reference_form
        except ReferenceForm.DoesNotExist:
            return None

    log_datetime_format = "%Y-%m-%d %H:%M:%S"

    @property
    def last_requested(self):
        """
        Returns the last date the reference was requested,
        or None if it is not known.
        """
        # Parse the comments field:
        dt = None
        for l in self.comments.split("\n"):
            m = re.match("Reference requested by .* on (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", l)
            if m is not None:
                dt = timezone.utc.localize(datetime.strptime(m.groups()[0], self.log_datetime_format))
        return dt

    def log_request_made(self, user, dt):
        self.comments = self.comments + \
            ("\nReference requested by user %s via online system on %s\n" % \
                 (user.username, dt.strftime(self.log_datetime_format)))

    class Meta:
        verbose_name = "Reference Metadata"
        verbose_name_plural = verbose_name
        ordering = ('application__date_submitted',
                    'application__officer__first_name',
                    'application__officer__last_name',
                    'referee_number')
        unique_together = (("application", "referee_number"),)


class ReferenceFormManager(models.Manager):
    # manager to reduce number of SQL queries, especially in admin
    use_for_related_fields = True
    def get_queryset(self):
        return super(ReferenceFormManager, self).get_queryset().select_related('reference_info__application__officer')


class ReferenceForm(models.Model):
    referee_name = models.CharField("name of referee", max_length=NAME_LENGTH,
                                    help_text=REFEREE_NAME_HELP_TEXT)
    how_long_known = models.CharField("how long/since when have you known the applicant?", max_length=150)
    capacity_known = models.TextField("in what capacity do you know the applicant?")
    known_offences = models.BooleanField("""The position for which the applicant is applying requires substantial contact with children and young people. To the best of your knowledge, does the applicant have any convictions/cautions/bindovers, for any criminal offences?""", blank=True, default=False)
    known_offences_details = models.TextField("If the answer is yes, please identify", blank=True)
    capability_children = models.TextField("Please comment on the applicant's capability of working with children and young people (ie. previous experience of similar work, sense of responsibility, sensitivity, ability to work with others, ability to communicate with children and young people, leadership skills)")
    character = models.TextField("Please comment on aspects of the applicants character (ie. Christian experience honesty, trustworthiness, reliability, disposition, faithful attendance at worship/prayer meetings.)")
    concerns = models.TextField("Have you ever had concerns about either this applicant's ability or suitability to work with children and young people? If you would prefer to discuss your concerns on the telephone and in confidence, please contact: " + settings.REFERENCE_CONCERNS_CONTACT_DETAILS)
    comments = models.TextField("Any other comments you wish to make", blank=True)
    date_created = models.DateField("date created")
    reference_info = models.OneToOneField(Reference, related_name='_reference_form')

    objects = ReferenceFormManager()

    def _get_applicant_name(self):
        o = self.reference_info.application.officer
        return "%s %s" % (o.first_name, o.last_name)

    applicant_name = property(_get_applicant_name)

    def __str__(self):
        officer = self.reference_info.application.officer
        return "Reference form for %s %s by %s" % (officer.first_name, officer.last_name, self.referee_name)

    def save(self, *args, **kwargs):
        retval = super(ReferenceForm, self).save(*args, **kwargs)
        # Update application form with name of referee
        ref_info = self.reference_info
        app = ref_info.application
        app.referees[ref_info.referee_number - 1].name = self.referee_name
        app.save()
        return retval

    class Meta:
        verbose_name = "Reference"


class InvitationManager(models.Manager):
    use_for_related_fields = True
    def get_queryset(self):
        return super(InvitationManager, self).get_queryset().select_related('officer', 'camp', 'camp__chaplain')


class Invitation(models.Model):
    officer = models.ForeignKey(User)
    camp = models.ForeignKey(Camp)
    date_added = models.DateField(default=date.today)
    notes = models.CharField(max_length=255, blank=True)

    objects = InvitationManager()

    def __str__(self):
        return "%s %s — camp %s" % (self.officer.first_name, self.officer.last_name, self.camp)


    class Meta:
        ordering = ('-camp__year', 'officer__first_name', 'officer__last_name')
        unique_together = (('officer', 'camp'),)


class CRBApplicationManager(models.Manager):
    use_for_related_fields = True
    def get_queryset(self):
        return super(CRBApplicationManager, self).get_queryset().select_related('officer')

    def get_for_camp(self, camp):
        """
        Returns the CRBs that might be valid for a camp (ignoring the camp
        officer list)
        """
        # This logic is duplicated in cciw.officers.views.stats
        return self.get_queryset().filter(completed__gte=camp.start_date - timedelta(settings.CRB_VALID_FOR))


class CRBApplication(models.Model):
    officer = models.ForeignKey(User)
    crb_number = models.CharField("Disclosure number", max_length=20)
    completed = models.DateField("Date of issue")

    objects = CRBApplicationManager()

    def __str__(self):
        return "CRB application for %s %s, %s" % (self.officer.first_name,
                                                  self.officer.last_name,
                                                  self.completed.strftime("%Y-%m-%d"))

    class Meta:
        verbose_name = "CRB Disclosure"
        verbose_name_plural = "CRB Disclosures"


class CRBFormLogManager(models.Manager):
    use_for_related_fields = True
    def get_queryset(self):
        return super(CRBFormLogManager, self).get_queryset().select_related('officer')


class CRBFormLog(models.Model):
    """
    Represents a log of a  CRB form sent to an officer
    """
    officer = models.ForeignKey(User)
    sent = models.DateTimeField("Date sent")

    objects = CRBFormLogManager()

    def __str__(self):
        return "Log of CRB form sent to %s %s on %s" % (self.officer.first_name,
                                                        self.officer.last_name,
                                                        self.sent.strftime("%Y-%m-%d"))

    class Meta:
        verbose_name = "CRB form log"
        verbose_name_plural = "CRB form logs"


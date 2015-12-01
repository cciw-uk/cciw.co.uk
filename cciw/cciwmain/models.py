from datetime import date

from colorful.fields import RGBColorField
from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.functional import cached_property
from django.utils.html import format_html

from cciw.cciwmain import signals

REFERENCE_CONTACT_ROLE_NAME = "Safeguarding co-ordinator"


class Site(models.Model):
    short_name = models.CharField("Short name", max_length=25, blank=False, unique=True)
    slug_name = models.SlugField("Machine name", max_length=25, blank=True, unique=True)
    long_name = models.CharField("Long name", max_length=50, blank=False)
    info = models.TextField("Description (HTML)")

    def __str__(self):
        return self.short_name

    def get_absolute_url(self):
        return reverse('cciw-cciwmain-sites_detail', kwargs=dict(slug=self.slug_name))

    def save(self, **kwargs):
        from django.template.defaultfilters import slugify
        if self.slug_name == "":
            self.slug_name = slugify(self.short_name)
        super(Site, self).save(**kwargs)


class Role(models.Model):
    name = models.CharField("Name", max_length=255,
                            help_text="Internal name of role, should remain fixed once created")
    description = models.CharField("Title", max_length=255,
                                   help_text="Public name/title of role")

    def __str__(self):
        return self.description


class Person(models.Model):
    name = models.CharField("Name", max_length=40)
    info = models.TextField("Information (Plain text)",
                            blank=True)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, verbose_name="Associated admin users",
                                   related_name='people',
                                   blank=True)
    phone_number = models.CharField("Phone number", max_length=40,
                                    blank=True,
                                    help_text="Required only for staff like CPO who need to be contacted.")
    roles = models.ManyToManyField(Role, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'people'


class CampName(models.Model):
    name = models.CharField(max_length=255, help_text="Name of set of camps. Should start with captial letter", unique=True)
    slug = models.SlugField(max_length=255, help_text="Name used in URLs and email addresses. Normally just the lowercase version of the name, with spaces replaces by -", unique=True)
    color = RGBColorField()

    def __str__(self):
        return self.name


class CampManager(models.Manager):
    use_for_related_fields = True

    def get_queryset(self):
        return super(CampManager, self).get_queryset().select_related('chaplain', 'camp_name').prefetch_related('leaders')

    def get_by_natural_key(self, year, slug):
        return self.get(year=year, camp_name__slug=slug)


class Camp(models.Model):
    year = models.PositiveSmallIntegerField("year")
    camp_name = models.ForeignKey(CampName, related_name='camps')
    old_name = models.CharField(max_length=50, blank=True)
    minimum_age = models.PositiveSmallIntegerField()
    maximum_age = models.PositiveSmallIntegerField()
    start_date = models.DateField("start date")
    end_date = models.DateField("end date")
    max_campers = models.PositiveSmallIntegerField("maximum campers", default=80)
    max_male_campers = models.PositiveSmallIntegerField("maximum male campers", default=60)
    max_female_campers = models.PositiveSmallIntegerField("maximum female campers", default=60)
    last_booking_date = models.DateField(null=True, blank=True, help_text="Camp start date will be used if left empty.")
    south_wales_transport_available = models.BooleanField("South Wales transport available (pre 2015 only)", default=False)

    chaplain = models.ForeignKey(Person,
                                 related_name="camps_as_chaplain",
                                 verbose_name="chaplain",
                                 null=True, blank=True)
    leaders = models.ManyToManyField(Person,
                                     related_name="camps_as_leader",
                                     verbose_name="leaders",
                                     blank=True)
    admins = models.ManyToManyField(settings.AUTH_USER_MODEL,
                                    related_name="camps_as_admin",
                                    verbose_name="admins",
                                    help_text="These users can manage references/applications for the camp. Not for normal officers.",
                                    blank=True)
    site = models.ForeignKey(Site)
    officers = models.ManyToManyField(settings.AUTH_USER_MODEL, through='officers.Invitation')

    objects = CampManager()

    def save(self, *args, **kwargs):
        new = self.id is None
        super(Camp, self).save(*args, **kwargs)
        if new:
            signals.camp_created.send(self)

    def natural_key(self):
        return (self.year, self.slug_name)

    def __str__(self):
        leaders = list(self.leaders.all())
        chaplain = None
        try:
            chaplain = self.chaplain
        except Person.DoesNotExist:
            # This might not be raised if we didn't use 'select_related',
            # instead self.chaplain could be None
            pass
        if chaplain is not None:
            leaders.append(chaplain)

        leadertext = self._format_leaders(leaders)
        return "%s (%s)" % (self.slug_name_with_year, leadertext)

    @cached_property
    def previous_camp(self):
        return (Camp.objects
                .filter(year__lt=self.year,
                        camp_name=self.camp_name)
                .order_by('-year')
                .first())

    @cached_property
    def next_camp(self):
        return (Camp.objects
                .filter(year__gt=self.year,
                        camp_name=self.camp_name)
                .order_by('year')
                .first())

    def _format_leaders(self, ls):
        if len(ls) > 0:
            return ", ".join(str(l) for l in ls)
        else:
            return ""

    @property
    def leaders_formatted(self):
        return self._format_leaders(list(self.leaders.all()))

    @property
    def name(self):
        return self.camp_name.name

    @property
    def slug_name(self):
        return self.camp_name.slug

    @property
    def slug_name_with_year(self):
        return "%s-%s" % (self.year, self.slug_name)

    @property
    def nice_name(self):
        return "Camp %s, year %d" % (self.name, self.year)

    @property
    def nice_dates(self):
        if self.start_date.month == self.end_date.month:
            return "{0} - {1} {2}".format(self.start_date.strftime('%e').strip(),
                                          self.end_date.strftime('%e').strip(),
                                          self.start_date.strftime('%B'))
        else:
            return "{0} - {1}".format(self.start_date.strftime('%e %B').strip(),
                                      self.end_date.strftime('%e %B').strip())

    def get_link(self):
        return format_html("<a href='{0}'>{1}</a>", self.get_absolute_url(), self.nice_name)

    def get_absolute_url(self):
        return reverse("cciw-cciwmain-camps_detail",
                       kwargs=dict(year=self.year, slug=self.slug_name))

    def is_past(self):
        return self.end_date <= date.today()

    @property
    def age(self):
        return "%d-%d" % (self.minimum_age, self.maximum_age)

    def get_places_left(self):
        """
        Return 3 tuple containing (places left, places left for boys, places left for girls).
        Note that the first isn't necessarily the sum of 2nd and 3rd.
        """
        from cciw.bookings.models import SEX_MALE, SEX_FEMALE
        females_booked = 0
        males_booked = 0
        q = self.bookings.booked().values_list('sex').annotate(count=models.Count("id")).order_by()
        for (s, c) in q:
            if s == SEX_MALE:
                males_booked = c
            elif s == SEX_FEMALE:
                females_booked = c
        total_booked = males_booked + females_booked
        # negative numbers of places available is confusing for our purposes, so use max
        return (max(self.max_campers - total_booked, 0),
                max(self.max_male_campers - males_booked, 0),
                max(self.max_female_campers - females_booked, 0))

    @property
    def closes_for_bookings_on(self):
        return self.last_booking_date if self.last_booking_date is not None else self.start_date

    def open_for_bookings(self, on_date):
        return on_date <= self.closes_for_bookings_on

    @property
    def is_open_for_bookings(self):
        return self.open_for_bookings(date.today())

    class Meta:
        ordering = ['-year', 'start_date']
        unique_together = [
            ('year', 'camp_name'),
        ]


def get_reference_contact_people():
    return list(Person.objects.filter(roles__name=REFERENCE_CONTACT_ROLE_NAME))


import cciw.cciwmain.hooks  # NOQA  isort:skip

from datetime import date

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.html import format_html

from cciw.cciwmain import signals


class Site(models.Model):
    short_name = models.CharField("Short name", max_length=25, blank=False, unique=True)
    slug_name = models.SlugField("Machine name", max_length=25, blank=True, unique=True)
    long_name = models.CharField("Long name", max_length=50, blank=False)
    info = models.TextField("Description (HTML)")

    def __str__(self):
        return self.short_name

    def get_absolute_url(self):
        return reverse('cciwmain.sites.detail', kwargs=dict(slug=self.slug_name))

    def save(self, **kwargs):
        from django.template.defaultfilters import slugify
        self.slug_name = slugify(self.short_name)
        super(Site, self).save(**kwargs)


class Person(models.Model):
    name = models.CharField("Name", max_length=40)
    info = models.TextField("Information (Plain text)",
                        blank=True)
    users = models.ManyToManyField(User, verbose_name="Associated admin users", blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'people'


class CampManager(models.Manager):
    use_for_related_fields = True
    def get_queryset(self):
        return super(CampManager, self).get_queryset().select_related('chaplain').prefetch_related('leaders')

    def get_by_natural_key(self, year, number):
        return self.get(year=year, number=number)


class Camp(models.Model):
    year = models.PositiveSmallIntegerField("year")
    number = models.PositiveSmallIntegerField("number")
    minimum_age = models.PositiveSmallIntegerField()
    maximum_age = models.PositiveSmallIntegerField()
    start_date = models.DateField("start date")
    end_date = models.DateField("end date")
    max_campers = models.PositiveSmallIntegerField("maximum campers", default=80)
    max_male_campers = models.PositiveSmallIntegerField("maximum male campers", default=60)
    max_female_campers = models.PositiveSmallIntegerField("maximum female campers", default=60)
    south_wales_transport_available = models.BooleanField("South Wales transport available (pre 2015 only)", default=False)

    previous_camp = models.ForeignKey("self",
        related_name="next_camps",
        verbose_name="previous camp",
        null=True, blank=True)
    chaplain = models.ForeignKey(Person,
        related_name="camps_as_chaplain",
        verbose_name="chaplain",
        null=True, blank=True)
    leaders = models.ManyToManyField(Person,
        related_name="camps_as_leader",
        verbose_name="leaders",
        blank=True)
    admins = models.ManyToManyField(User,
        related_name="camps_as_admin",
        verbose_name="admins",
        help_text="These users can manage references/applications for the camp. Not for normal officers.",
        blank=True)
    site = models.ForeignKey(Site)
    online_applications = models.BooleanField("Accepts online applications from officers.", default=True)
    officers = models.ManyToManyField(User, through='officers.Invitation')

    objects = CampManager()

    def save(self, *args, **kwargs):
        new = self.id is None
        super(Camp, self).save(*args, **kwargs)
        if new:
            signals.camp_created.send(self)

    def natural_key(self):
        return (self.year, self.number)

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
        return u"%s-%s (%s)" % (self.year, self.number, leadertext)

    def _format_leaders(self, ls):
        if len(ls) > 0:
            return u", ".join(str(l) for l in ls)
        else:
            return u""

    @property
    def leaders_formatted(self):
        return self._format_leaders(list(self.leaders.all()))

    @property
    def nice_name(self):
        return u"Camp %d, year %d" % (self.number, self.year)

    def get_link(self):
        return format_html(u"<a href='{0}'>{1}</a>", self.get_absolute_url(), self.nice_name)

    def get_absolute_url(self):
        return "/camps/{0}/{1}/".format(self.year, self.number)

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

    def is_booking_open(self):
        from cciw.bookings.views import is_booking_open
        return is_booking_open(self.year)

    class Meta:
        ordering = ['-year','number']
        unique_together = (('year', 'number'),)


import cciw.cciwmain.hooks

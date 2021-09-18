import os.path
from datetime import date

from colorful.fields import RGBColorField
from django.conf import settings
from django.db import models
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.html import format_html

from .common import CampId


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
        super().save(**kwargs)


class Person(models.Model):
    name = models.CharField("Name", max_length=40)
    info = models.TextField("Information (Plain text)",
                            blank=True)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, verbose_name="Associated admin users",
                                   related_name='people',
                                   blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'people'


class CampName(models.Model):
    name = models.CharField(max_length=255, help_text="Name of set of camps. Should start with capital letter", unique=True)
    slug = models.SlugField(max_length=255, help_text="Name used in URLs and email addresses. Normally just the lowercase version of the name, with spaces replaces by -", unique=True)
    color = RGBColorField()

    def __str__(self):
        return self.name


class CampManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().select_related('chaplain', 'camp_name').prefetch_related('leaders')

    def get_by_natural_key(self, year, slug):
        return self.get(year=year, camp_name__slug=slug)


class CampQuerySet(models.QuerySet):

    def include_other_years_info(self):
        return self.prefetch_related('camp_name__camps')


class Camp(models.Model):
    year = models.PositiveSmallIntegerField("year")
    camp_name = models.ForeignKey(CampName,
                                  on_delete=models.PROTECT,
                                  related_name='camps')
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
                                 on_delete=models.PROTECT,
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
    site = models.ForeignKey(Site,
                             on_delete=models.PROTECT)

    officers = models.ManyToManyField(settings.AUTH_USER_MODEL, through='officers.Invitation')

    special_info_html = models.TextField(verbose_name='Special information', default='',
                                         blank=True,
                                         help_text='HTML, displayed at the top of the camp details page')

    objects = CampManager.from_queryset(CampQuerySet)()

    class Meta:
        ordering = ['-year', 'start_date']
        unique_together = [
            ('year', 'camp_name'),
        ]
        base_manager_name = 'objects'

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
        return f"{self.url_id} ({leadertext})"

    @cached_property
    def previous_camp(self):
        if self._state.fields_cache.get('camp_name', None) is not None:
            camp_name = self.camp_name
            if hasattr(camp_name, '_prefetched_objects_cache'):
                other_camps = camp_name._prefetched_objects_cache.get('camps', None)
                if other_camps is not None:
                    previous_camps = [c for c in other_camps if c.year < self.year]
                    previous_camps.sort(key=lambda c: -c.year)
                    if previous_camps:
                        return previous_camps[0]
                    else:
                        return None

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

    def _format_leaders(self, leaders):
        if len(leaders) > 0:
            return ", ".join(str(leader) for leader in leaders)
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
    def url_id(self):
        """
        'camp_id' used in URLs
        """
        return CampId(self.year, self.slug_name)

    @property
    def camp_ids_for_stats(self):
        camps = [self.previous_camp, self] if self.previous_camp else [self]
        return [c.url_id for c in camps]

    @property
    def nice_name(self):
        return f"Camp {self.name}, year {self.year}"

    @property
    def bracketted_old_name(self):
        return (f" (Camp {self.old_name})" if self.old_name else "")

    @property
    def nice_dates(self):
        if self.start_date.month == self.end_date.month:
            return "{} - {} {}".format(self.start_date.strftime('%e').strip(),
                                       self.end_date.strftime('%e').strip(),
                                       self.start_date.strftime('%B'))
        else:
            return "{} - {}".format(self.start_date.strftime('%e %B').strip(),
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
        return f"{self.minimum_age}-{self.maximum_age}"

    def get_places_left(self):
        """
        Return 3 tuple containing (places left, places left for boys, places left for girls).
        Note that the first isn't necessarily the sum of 2nd and 3rd.
        """
        from cciw.bookings.models import Sex
        females_booked = 0
        males_booked = 0
        q = self.bookings.booked().values_list('sex').annotate(count=models.Count("id")).order_by()
        for (s, c) in q:
            if s == Sex.MALE:
                males_booked = c
            elif s == Sex.FEMALE:
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


def generate_colors_less(update_existing=False):
    # We could do this as a dynamic view, but we'd lose several benefits:
    #  - django-compressor wouldn't be able to find it and bundle it with
    #    other less files
    #  - therefore wouldn't be able to use it for mixins that are imported
    #    by styles.less
    camp_names = CampName.objects.all()
    colors_less = render_to_string('cciw/camps/camp_colors_tpl.less',
                                   {'names': camp_names}).encode('utf-8')
    paths = [os.path.join(settings.PROJECT_ROOT, settings.COLORS_LESS_DIR, settings.COLORS_LESS_FILE),  # dev
             os.path.join(settings.STATIC_ROOT, settings.COLORS_LESS_FILE)]  # production
    for p in paths:
        if os.path.exists(os.path.dirname(p)):
            if update_existing or not os.path.exists(p):
                with open(p, "wb") as f:
                    f.write(colors_less)

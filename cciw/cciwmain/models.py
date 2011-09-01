import datetime

from django.contrib.auth.models import User
from django.db import models
from django.utils.safestring import mark_safe

from cciw.cciwmain import signals


class Site(models.Model):
    short_name = models.CharField("Short name", max_length="25", blank=False, unique=True)
    slug_name = models.SlugField("Machine name", max_length="25", blank=True, unique=True)
    long_name = models.CharField("Long name", max_length="50", blank=False)
    info = models.TextField("Description (HTML)")

    def __unicode__(self):
        return self.short_name

    def get_absolute_url(self):
        return u"/sites/%s/" % self.slug_name

    def save(self):
        from django.template.defaultfilters import slugify
        self.slug_name = slugify(self.short_name)
        super(Site, self).save()


class Person(models.Model):
    name = models.CharField("Name", max_length=40)
    info = models.TextField("Information (Plain text)",
                        blank=True)
    users = models.ManyToManyField(User, verbose_name="Associated admin users", blank=True)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'people'


class CampManager(models.Manager):
    use_for_related_fields = True
    def get_query_set(self):
        return super(CampManager, self).get_query_set().select_related('chaplain')

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
        null=True, blank=True)
    admins = models.ManyToManyField(User,
        related_name="camps_as_admin",
        verbose_name="admins",
        help_text="These users can manage references/applications for the camp. Not for normal officers.",
        null=True, blank=True)
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

    def __unicode__(self):
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
        return mark_safe(u"<a href='%s'>%s</a>" % (self.get_absolute_url(), self.nice_name))

    def get_absolute_url(self):
        return u"/camps/%d/%d/" % (self.year, self.number)

    def is_past(self):
        return self.end_date <= datetime.date.today()

    @property
    def age(self):
        return "%d-%d" % (self.minimum_age, self.maximum_age)

    def get_places_left(self, sex=None):
        from cciw.bookings.models import SEX_MALE, SEX_FEMALE
        qs = self.bookings.booked()
        if sex is not None:
            qs = qs.filter(sex=sex)
        booked = qs.count()

        if sex is None:
            retval = self.max_campers - booked
        elif sex == SEX_MALE:
            retval = self.max_male_campers - booked
        elif sex == SEX_FEMALE:
            retval = self.max_female_campers - booked
        else:
            assert False, "%s is not a valid sex" % sex
        return max(0, retval) # negative numbers of places available is confusing for our purposes

    class Meta:
        ordering = ['-year','number']
        unique_together = (('year', 'number'),)




import cciw.cciwmain.hooks

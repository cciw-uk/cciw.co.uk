import datetime

from cciw.cciwmain import signals
from django.db import models
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe

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

    class Meta:
        app_label = "cciwmain"
        pass

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
        app_label = "cciwmain"

CAMP_AGES = (
    (u'Jnr',u'Junior'),
    (u'Snr',u'Senior')
)

class CampManager(models.Manager):
    use_for_related_fields = True
    def get_query_set(self):
        return super(CampManager, self).get_query_set().select_related('chaplain')

    def get_by_natural_key(self, year, number):
        return self.get(year=year, number=number)


class Camp(models.Model):
    year = models.PositiveSmallIntegerField("year")
    number = models.PositiveSmallIntegerField("number")
    age = models.CharField("age", blank=False, max_length=3,
                        choices=CAMP_AGES)
    start_date = models.DateField("start date")
    end_date = models.DateField("end date")
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

    def save(self):
        new = self.id is None
        super(Camp, self).save()
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

    class Meta:
        app_label = "cciwmain"
        ordering = ['-year','number']
        unique_together = (('year', 'number'),)

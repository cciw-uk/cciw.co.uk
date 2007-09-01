import datetime

from django.db import models
from django.contrib.auth.models import User

class Site(models.Model):
    short_name = models.CharField("Short name", maxlength="25", blank=False, unique=True)
    slug_name = models.SlugField("Machine name", maxlength="25", blank=True, unique=True)
    long_name = models.CharField("Long name", maxlength="50", blank=False)
    info = models.TextField("Description (HTML)")
    
    def __unicode__(self):
        return self.short_name
        
    def get_absolute_url(self):
        return "/sites/" + self.slug_name
    
    def save(self):
        from django.template.defaultfilters import slugify
        self.slug_name = slugify(self.short_name)
        super(Site, self).save()
    
    class Meta:
        app_label = "cciwmain"
        pass
    
    class Admin:
        fields = (
            (None, {'fields': ('short_name', 'long_name', 'info')}),
        )
        
class Person(models.Model):
    name = models.CharField("Name", maxlength=40)
    info = models.TextField("Information (Plain text)", 
                        blank=True)
    user = models.ForeignKey(User, verbose_name="Associated admin user", null=True, blank=True)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'people'
        app_label = "cciwmain"
        
    class Admin:
        pass

CAMP_AGES = (
    (u'Jnr',u'Junior'),
    (u'Snr',u'Senior')
)

class Camp(models.Model):
    year = models.PositiveSmallIntegerField("year")
    number = models.PositiveSmallIntegerField("number")
    age = models.CharField("age", blank=False, maxlength=3,
                        choices=CAMP_AGES)
    start_date = models.DateField("start date")
    end_date = models.DateField("end date")
    previous_camp = models.ForeignKey("self", 
        related_name="next_camps", 
        verbose_name="previous camp",
        null=True, blank=True)
    chaplain = models.ForeignKey(Person, 
        related_name="camp_as_chaplain", 
        verbose_name="chaplain", 
        null=True, blank=True)
    leaders = models.ManyToManyField(Person, 
        related_name="camp_as_leader", 
        verbose_name="leaders",
        null=True, blank=True, filter_interface=models.HORIZONTAL)
    site = models.ForeignKey(Site)
    online_applications = models.BooleanField("Accepts online applications from officers.")
    
    def __unicode__(self):
        leaders = list(self.leaders.all())
        try:
            leaders.append(self.chaplain)
        except Person.DoesNotExist:
            pass
        if len(leaders) > 0:
            leadertext = u" (" + u", ".join(str(l) for l in leaders) + u")"
        else:
            leadertext = u""
        return unicode(self.year) + u"-" + unicode(self.number) + leadertext
    
    @property
    def nice_name(self):
        return u"Camp %d, year %d"  % (self.number, self.year)

    def get_link(self):
        return u"<a href='%s'>%s</a>" % (self.get_absolute_url(), self.nice_name)

    def get_absolute_url(self):
        return u"/camps/%d/%d/" %  (self.year, self.number)

    def is_past(self):
        return self.end_date <= datetime.date.today()

    class Meta:
        app_label = "cciwmain"
        ordering = ['-year','number']

    class Admin:
        fields = (
            (None, {'fields': ('year', 'number', 'age', 'start_date', 'end_date', 
                               'chaplain', 'leaders', 'site', 'previous_camp', 'online_applications') 
                    }
            ),
        )
        ordering = ['-year','number']
        list_filter = ('age', 'site', 'online_applications')

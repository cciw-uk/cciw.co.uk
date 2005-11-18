from django.core import meta

class Site(meta.Model):
    short_name = meta.CharField("Short name", maxlength="25", blank=False, unique=True)
    slug_name = meta.SlugField("Machine name", maxlength="25", blank=True, unique=True)
    long_name = meta.CharField("Long name", maxlength="50", blank=False)
    info = meta.TextField("Description (HTML)")
    
    def __repr__(self):
        return self.short_name
        
    def get_absolute_url(self):
        return "/sites/" + self.slug_name
    
    def _pre_save(self):
        from django.core.template.defaultfilters import slugify
        self.slug_name = slugify(self.short_name, "")
    
    class META:
        admin = meta.Admin(
            fields = (
                (None, {'fields': ('short_name', 'long_name', 'info')}),
            )
        )
        
class Person(meta.Model):
    name = meta.CharField("Name", maxlength=40)
    info = meta.TextField("Information (Plain text)", 
                        blank=True)
    def __repr__(self):
        return self.name

    class META:
        admin = meta.Admin()
        ordering= ('name',)
        verbose_name_plural = 'people'
    

CAMP_AGES = (
    ('Jnr','Junior'),
    ('Snr','Senior')
)

class Camp(meta.Model):
    year = meta.PositiveSmallIntegerField("year")
    number = meta.PositiveSmallIntegerField("number")
    age = meta.CharField("age", blank=False, maxlength=3,
                        choices=CAMP_AGES)
    start_date = meta.DateField("start date")
    end_date = meta.DateField("end date")
    previous_camp = meta.ForeignKey("self", 
        related_name="next_camp", 
        verbose_name="previous camp",
        null=True, blank=True)
    chaplain = meta.ForeignKey(Person, 
        related_name="camp_as_chaplain", 
        verbose_name="chaplain", 
        null=True, blank=True)
    leaders = meta.ManyToManyField(Person, 
        singular="leader",
        related_name="camp_as_leader", 
        verbose_name="leaders",
        null=True, blank=True)
    site = meta.ForeignKey(Site)
    
    def __repr__(self):
        from django.models.camps import persons
        leaders = self.get_leader_list()
        try:
            leaders += [self.get_chaplain()]
        except persons.PersonDoesNotExist:
            pass
        if len(leaders) > 0:
            leadertext = " (" + ", ".join([repr(l) for l in leaders]) + ")"
        else:
            leadertext = ""
        return str(self.year) + "-" + str(self.number) + leadertext
        
    def nice_name(self):
        return "Camp " + str(self.number) + ", year " + str(self.year)

    def get_link(self):
        return "<a href='" + self.get_absolute_url() + "'>" + self.nice_name() + '</a>'

    def get_absolute_url(self):
        from cciw.apps.cciw.settings import *
        return "/camps/" + str(self.year) + "/" + str(self.number) + "/"

    class META:
        admin = meta.Admin(
            fields = (
                (None, {'fields': ('year', 'number', 'age', 'start_date', 'end_date', 
                                   'chaplain', 'leaders', 'site', 'previous_camp') 
                        }
                ),
            )
        )
        ordering = ['-year','number']

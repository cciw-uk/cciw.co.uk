from django.core import meta

class Site(meta.Model):
	short_name = meta.CharField("Short name", maxlength="25", blank=False, unique=True)
	slug_name = meta.SlugField("Machine name", maxlength="25", blank=True, unique=True)
	long_name = meta.CharField("Long name", maxlength="50", blank=False)
	info = meta.TextField("Description (HTML)")
	class META:
		admin = meta.Admin(
			fields = (
				(None, {'fields': ('short_name', 'long_name', 'info')}),
			)
		)
	
	def __repr__(self):
		return self.short_name
		
	def get_absolute_url(self):
		return "/sites/" + self.slug_name
	
	def _pre_save(self):
		from django.core.defaultfilters import slugify
		self.slug_name = slugify(self.short_name, "")
	
class Person(meta.Model):
	name = meta.CharField("Name", maxlength=40)
	info = meta.TextField("Information (Plain text)", 
						blank=True)
	class META:
		admin = meta.Admin()
		ordering= ('name',)
		verbose_name_plural = 'people'
	
	def __repr__(self):
		return self.name


CAMP_AGES = (
	('Jnr','Junior'),
	('Snr','Senior')
)

class Camp(meta.Model):
	year = meta.PositiveSmallIntegerField("year")
	number = meta.PositiveSmallIntegerField("number")
	age = meta.CharField("age", blank=False, maxlength=3,
						choices=CAMP_AGES)
	startDate = meta.DateField("start date")
	endDate = meta.DateField("end date")
	previousCamp = meta.ForeignKey("self", 
		related_name="nextCamp", 
		verbose_name="previous camp",
		null=True, blank=True)
	chaplain = meta.ForeignKey(Person, 
		related_name="campAsChaplain", 
		verbose_name="chaplain", 
		null=True, blank=True)
	leaders = meta.ManyToManyField(Person, 
		related_name="campAsLeader", 
		verbose_name="leaders",
		null=True, blank=True)
	site = meta.ForeignKey(Site)
	class META:
		admin = meta.Admin(
			fields = (
				(None, {'fields': ('year', 'number', 'age', 'startDate', 'endDate', 'chaplain', 'leaders', 'site', 'previousCamp') }),
			)
		)
		ordering = ['-year','number']
	
	def __repr__(self):
		from django.models.camps import persons
		leaders = self.get_person_list()
		try:
			leaders += [self.get_chaplain()]
		except persons.PersonDoesNotExist:
			pass
		if len(leaders) > 0:
			leadertext = " (" + ", ".join([repr(l) for l in leaders]) + ")"
		else:
			leadertext = ""
		return str(self.year) + "-" + str(self.number) + leadertext
		
	def niceName(self):
		return "Camp " + str(self.number) + ", year " + str(self.year)
	
	def get_absolute_url(self):
		return "/camps/" + str(self.year) + "/" + str(self.number) + "/"


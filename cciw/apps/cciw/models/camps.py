from django.core import meta

class Site(meta.Model):
	short_name = meta.CharField("Short name", maxlength="25", blank=False)
	long_name = meta.CharField("Long name", maxlength="50", blank=False)
	info = meta.TextField("Description (HTML)")
	class META:
		admin = meta.Admin()
	
	def __repr__(self):
		return self.short_name
	
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
	year = meta.PositiveSmallIntegerField("Year")
	number = meta.PositiveSmallIntegerField("Number")
	age = meta.CharField("Age", blank=False, maxlength=3,
						choices=CAMP_AGES)
	dates = meta.CharField("Dates", maxlength=20)
	previousCamp = meta.ForeignKey("self", 
		related_name="nextCamps", 
		verbose_name="previous camp",
		null=True, blank=True)
	chaplain = meta.ForeignKey(Person, 
		related_name="chaplainOnCamps", 
		verbose_name="chaplain", 
		null=True, blank=True)
	leaders = meta.ManyToManyField(Person, 
		related_name="leaderOnCamps", 
		verbose_name="leaders",
		null=True, blank=True)
	site = meta.ForeignKey(Site)
	class META:
		admin = meta.Admin(
			fields = (
				(None, {'fields': ('year', 'number', 'age', 'dates', 'chaplain', 'leaders', 'site', 'previousCamp') }),
			)
		)
		ordering = ['-year','number']
	
	def __repr__(self):
		return str(self.year) + "-" + str(self.number)
	
	def get_absolute_url(self):
		return "/camps/" + str(self.year) + "/" + str(self.number) + "/"


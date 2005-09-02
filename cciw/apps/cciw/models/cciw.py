from django.core import meta

# Create your models here.

class Person(meta.Model):
	name = meta.CharField("Name", maxlength=40)
	info = meta.TextField("Information (HTML)")

class Site(meta.Model):
	short_name = meta.CharField("Short name", maxlength="25", blank=False)
	long_name = meta.CharField("Long name", maxlength="50", blank=False)
	info = meta.TextField("Description (HTML)")

class Camp(meta.Model):
	year = meta.IntegerField("Year")
	age = meta.CharField("Age", blank=False, maxlength=3,
				choices=(
						('Jnr','Junior'),
						('Snr','Senior')
					)
				)
	dates = meta.CharField("Dates", maxlength=20)
	previousCamps = meta.ForeignKey("self", related_name="nextCamps")
	chaplain = meta.ForeignKey(Person, related_name="chaplainOnCamps")
	leaders = meta.ManyToManyField(Person, related_name="leaderOnCamps")
	site = meta.ForeignKey(Site)





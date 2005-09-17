from django.core import meta
from members import *

class Gallery(meta.Model):
	location = meta.CharField("Location/URL", maxlength=50)
	needsApproval = meta.BooleanField("Photos need approval", default=False)

	def __repr__(self):
		return self.location
		
	class META:
		admin = meta.Admin()
		verbose_name_plural = "Galleries"
		ordering = ('-location',)

class Photo(meta.Model):
	createdAt = meta.DateTimeField("Started", null=True)
	open = meta.BooleanField("Open")
	hidden = meta.BooleanField("Hidden")
	filename = meta.CharField("Filename", maxlength=50)
	gallery = meta.ForeignKey(Gallery,
		verbose_name="gallery",
		related_name="photo")
	checkedBy = meta.ForeignKey(Member,
		null=True, blank=True, related_name="checkedPhoto")
	approved = meta.BooleanField("Approved", null=True, blank=True)
	needsApproval = meta.BooleanField("Needs approval", default=False)
	
	def __repr__(self):
		return self.filename
	
	class META:
		admin = meta.Admin()
	

from django.core import meta
from users import *
from polls import *
from photos import *

class Forum(meta.Model):
	open = meta.BooleanField("Open", default=True)
	location = meta.CharField("Location/URL", maxlength=50)
	
	def __repr__(self):
		return self.location
		
	class META:
		admin = meta.Admin()

class NewsItem(meta.Model):
	createdBy = meta.ForeignKey(User, related_name="newsItemCreated")
	createdAt = meta.DateTimeField("Posted")
	summary = meta.TextField("Summary")
	fullItem = meta.TextField("Full post", blank=True)
	subject = meta.CharField("Subject", maxlength=100)
	
	class META:
		admin = meta.Admin()
	
	def __repr__(self):
		return self.subject
	

class Topic(meta.Model):
	subject = meta.CharField("Subject", maxlength=100)
	startedBy = meta.ForeignKey(User, related_name="topicStarted",
		verbose_name="started by")
	createdAt = meta.DateTimeField("Started", null=True)
	open = meta.BooleanField("Open")
	hidden = meta.BooleanField("Hidden")
	checkedBy = meta.ForeignKey(User,
		null=True, blank=True, related_name="topicChecked",
		verbose_name="checked by")
	approved = meta.BooleanField("Approved", null=True, blank=True)
	needsApproval = meta.BooleanField("Needs approval", default=False)
	newsItem = meta.ForeignKey(NewsItem, null=True, blank=True,
		related_name="topic") # optional news item
	poll = meta.ForeignKey(Poll, null=True, blank=True,
		related_name="topic") # optional topic
	forum = meta.ForeignKey(Forum,
		related_name="topic")

	class META:
		admin = meta.Admin(
			list_display = ('subject', 'startedBy', 'createdAt'),
			search_fields = ('subject',)
		)
		ordering = ('-startedBy',)
		
	def __repr__(self):
		return  self.subject
	
class Post(meta.Model):
	postedBy = meta.ForeignKey(User, 
		related_name="post")
	subject = meta.CharField("Subject", maxlength=100) # deprecated, supports legacy boards
	message = meta.TextField("Message")
	postedAt = meta.DateTimeField("Posted at", null=True)
	hidden = meta.BooleanField("Hidden", default=False)
	checkedBy = meta.ForeignKey(User,
		verbose_name="checked by",
		null=True, blank=True, related_name="checkedPost")
	approved = meta.BooleanField("Approved", null=True)
	needsApproval = meta.BooleanField("Needs approval", default=False)
	topic = meta.ForeignKey(Topic, related_name="post",
		null=True, blank=True)
	photo = meta.ForeignKey(Photo, related_name="post",
		null=True, blank=True)
		
	def __repr__(self):
		return "[" + str(self.id) + "]  " + self.message[:30]
	
	class META:
		admin = meta.Admin(
			list_display = ('__repr__', 'postedBy', 'postedAt'),
			search_fields = ('message',)
		)
		ordering = ('postedAt',)
		

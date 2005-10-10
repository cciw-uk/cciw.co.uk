from django.core import meta
from members import *
from polls import *

class Forum(meta.Model):
	open = meta.BooleanField("Open", default=True)
	location = meta.CharField("Location/path", db_index=True, unique=True, maxlength=50)
	
	def get_absolute_url(self):
		return '/' + self.location
	
	def __repr__(self):
		return self.location
		
	class META:
		admin = meta.Admin()

class NewsItem(meta.Model):
	createdBy = meta.ForeignKey(Member, related_name="newsItemCreated")
	createdAt = meta.DateTimeField("Posted")
	summary = meta.TextField("Summary")
	fullItem = meta.TextField("Full post", blank=True)
	subject = meta.CharField("Subject", maxlength=100)
	
	def __repr__(self):
		return self.subject
	
	class META:
		admin = meta.Admin()
	
	

class Topic(meta.Model):
	subject = meta.CharField("Subject", maxlength=100)
	startedBy = meta.ForeignKey(Member, related_name="topicStarted",
		verbose_name="started by")
	createdAt = meta.DateTimeField("Started", null=True)
	open = meta.BooleanField("Open")
	hidden = meta.BooleanField("Hidden")
	checkedBy = meta.ForeignKey(Member,
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
	lastPostAt = meta.DateTimeField("Last post at", 
		null=True, blank=True) # needed for performance and simplicity in templates
	lastPostBy = meta.ForeignKey(Member, verbose_name="Last post by",
		null=True, blank=True) # needed for performance and simplicity in templates
	postCount = meta.PositiveSmallIntegerField("Number of posts") # since we need 'lastPost', may as well have this too
		
	def __repr__(self):
		return  self.subject
		
	def get_absolute_url(self):
		return self.get_forum().get_absolute_url() + str(self.id) + '/'
	
	def get_link(self):
		return '<a href="' + self.get_absolute_url() + '">' + self.subject + '</a>'

	class META:
		admin = meta.Admin(
			list_display = ('subject', 'startedBy', 'createdAt'),
			search_fields = ('subject',)
		)
		ordering = ('-startedBy',)

class Gallery(meta.Model):
	location = meta.CharField("Location/URL", maxlength=50)
	needsApproval = meta.BooleanField("Photos need approval", default=False)

	def __repr__(self):
		return self.location
		
	def get_absolute_url(self):
		return '/' + self.location
		
	class META:
		admin = meta.Admin()
		verbose_name_plural = "Galleries"
		ordering = ('-location',)

class Photo(meta.Model):
	createdAt = meta.DateTimeField("Started", null=True)
	open = meta.BooleanField("Open")
	hidden = meta.BooleanField("Hidden")
	filename = meta.CharField("Filename", maxlength=50)
	description = meta.CharField("Description", blank=True, maxlength=100)
	gallery = meta.ForeignKey(Gallery,
		verbose_name="gallery",
		related_name="photo")
	checkedBy = meta.ForeignKey(Member,
		null=True, blank=True, related_name="checkedPhoto")
	approved = meta.BooleanField("Approved", null=True, blank=True)
	needsApproval = meta.BooleanField("Needs approval", default=False)
	lastPostAt = meta.DateTimeField("Last post at", 
		null=True, blank=True) # needed for performance and simplicity in templates
	lastPostBy = meta.ForeignKey(Member, verbose_name="Last post by",
		null=True, blank=True) # needed for performance and simplicity in templates
	postCount = meta.PositiveSmallIntegerField("Number of posts") # since we need 'lastPost', may as well have this too
	
	def __repr__(self):
		return self.filename
	
	def get_absolute_url(self):
		return self.get_gallery().get_absolute_url() + str(self.id) + '/'
		
	class META:
		admin = meta.Admin()
	
		
class Post(meta.Model):
	postedBy = meta.ForeignKey(Member, 
		related_name="post")
	subject = meta.CharField("Subject", maxlength=100) # deprecated, supports legacy boards
	message = meta.TextField("Message")
	postedAt = meta.DateTimeField("Posted at", null=True)
	hidden = meta.BooleanField("Hidden", default=False)
	checkedBy = meta.ForeignKey(Member,
		verbose_name="checked by",
		null=True, blank=True, related_name="checkedPost")
	approved = meta.BooleanField("Approved", null=True)
	needsApproval = meta.BooleanField("Needs approval", default=False)
	photo = meta.ForeignKey(Photo, related_name="post",
		null=True, blank=True)
	topic = meta.ForeignKey(Topic, related_name="post",
		null=True, blank=True)

		
	def __repr__(self):
		return "[" + str(self.id) + "]  " + self.message[:30]
		
	def updateParent(self, parent):
		"Update the cached info in the parent topic/photo"
		# Both types of parent, photos and topics,
		# are covered by this sub since they deliberately have the same
		# interface for this bit.
		postCount = parent.get_post_count()
		changed = False
		if (parent.lastPostAt is None and not self.postedAt is None) or \
			(not parent.lastPostAt is None and not self.postedAt is None \
			and self.postedAt > parent.lastPostAt):
			parent.lastPostAt = self.postedAt
			changed = True
		if parent.lastPostBy_id is None or \
			parent.lastPostBy_id != self.postedBy_id:
			parent.lastPostBy_id = self.postedBy_id
			changed = True
		if postCount > parent.postCount:
			parent.postCount = postCount
			changed = True
		if changed:
			parent.save()
				
	def _post_save(self):
		# Update parent topic/photo
		
		if not self.topic_id is None:
			self.updateParent(self.get_topic())
			
		if not self.photo_id is None:
			self.updateParent(self.get_photo())
		

	
	class META:
		admin = meta.Admin(
			list_display = ('__repr__', 'postedBy', 'postedAt'),
			search_fields = ('message',)
		)
		
		# Order by the autoincrement id, rather than  postedAt, because
		# this matches the old system (in the old system editing a post 
		# would also cause its postedAt date to change, but not it's order,
		# and data for the original post date/time is now lost)
		ordering = ('id',) 
		

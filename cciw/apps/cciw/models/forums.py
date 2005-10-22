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
    created_by = meta.ForeignKey(Member, related_name="news_item_created")
    created_at = meta.DateTimeField("Posted")
    summary = meta.TextField("Summary")
    full_item = meta.TextField("Full post", blank=True)
    subject = meta.CharField("Subject", maxlength=100)
    
    def __repr__(self):
        return self.subject
    
    class META:
        admin = meta.Admin()
    
    

class Topic(meta.Model):
    subject = meta.CharField("Subject", maxlength=100)
    started_by = meta.ForeignKey(Member, related_name="topic_started",
        verbose_name="started by")
    created_at = meta.DateTimeField("Started", null=True)
    open = meta.BooleanField("Open")
    hidden = meta.BooleanField("Hidden")
    checked_by = meta.ForeignKey(Member,
        null=True, blank=True, related_name="topic_checked",
        verbose_name="checked by")
    approved = meta.BooleanField("Approved", null=True, blank=True)
    needs_approval = meta.BooleanField("Needs approval", default=False)
    news_item = meta.ForeignKey(NewsItem, null=True, blank=True,
        related_name="topic") # optional news item
    poll = meta.ForeignKey(Poll, null=True, blank=True,
        related_name="topic") # optional topic
    forum = meta.ForeignKey(Forum,
        related_name="topic")
    last_post_at = meta.DateTimeField("Last post at", 
        null=True, blank=True) # needed for performance and simplicity in templates
    last_post_by = meta.ForeignKey(Member, verbose_name="Last post by",
        null=True, blank=True) # needed for performance and simplicity in templates
    post_count = meta.PositiveSmallIntegerField("Number of posts") # since we need 'lastPost', may as well have this too
        
    def __repr__(self):
        return  self.subject
        
    def get_absolute_url(self):
        return self.get_forum().get_absolute_url() + str(self.id) + '/'
    
    def get_link(self):
        return '<a href="' + self.get_absolute_url() + '">' + self.subject + '</a>'

    class META:
        admin = meta.Admin(
            list_display = ('subject', 'started_by', 'created_at'),
            search_fields = ('subject',)
        )
        ordering = ('-started_by',)

class Gallery(meta.Model):
    location = meta.CharField("Location/URL", maxlength=50)
    needs_approval = meta.BooleanField("Photos need approval", default=False)

    def __repr__(self):
        return self.location
        
    def get_absolute_url(self):
        return '/' + self.location
        
    class META:
        admin = meta.Admin()
        verbose_name_plural = "Galleries"
        ordering = ('-location',)

class Photo(meta.Model):
    created_at = meta.DateTimeField("Started", null=True)
    open = meta.BooleanField("Open")
    hidden = meta.BooleanField("Hidden")
    filename = meta.CharField("Filename", maxlength=50)
    description = meta.CharField("Description", blank=True, maxlength=100)
    gallery = meta.ForeignKey(Gallery,
        verbose_name="gallery",
        related_name="photo")
    checked_by = meta.ForeignKey(Member,
        null=True, blank=True, related_name="checked_photo")
    approved = meta.BooleanField("Approved", null=True, blank=True)
    needs_approval = meta.BooleanField("Needs approval", default=False)
    last_post_at = meta.DateTimeField("Last post at", 
        null=True, blank=True) # needed for performance and simplicity in templates
    last_post_by = meta.ForeignKey(Member, verbose_name="Last post by",
        null=True, blank=True) # needed for performance and simplicity in templates
    post_count = meta.PositiveSmallIntegerField("Number of posts") # since we need 'lastPost', may as well have this too
    
    def __repr__(self):
        return self.filename
    
    def get_absolute_url(self):
        return self.get_gallery().get_absolute_url() + str(self.id) + '/'
        
    class META:
        admin = meta.Admin()
    
        
class Post(meta.Model):
    posted_by = meta.ForeignKey(Member, 
        related_name="post")
    subject = meta.CharField("Subject", maxlength=100) # deprecated, supports legacy boards
    message = meta.TextField("Message")
    posted_at = meta.DateTimeField("Posted at", null=True)
    hidden = meta.BooleanField("Hidden", default=False)
    checked_by = meta.ForeignKey(Member,
        verbose_name="checked by",
        null=True, blank=True, related_name="checked_post")
    approved = meta.BooleanField("Approved", null=True)
    needs_approval = meta.BooleanField("Needs approval", default=False)
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
        post_count = parent.get_post_count()
        changed = False
        if (parent.last_post_at is None and not self.posted_at is None) or \
            (not parent.last_post_at is None and not self.posted_at is None \
            and self.posted_at > parent.last_post_at):
            parent.last_post_at = self.posted_at
            changed = True
        if parent.last_post_by_id is None or \
            parent.last_post_by_id != self.posted_by_id:
            parent.last_post_by_id = self.posted_by_id
            changed = True
        if post_count > parent.post_count:
            parent.post_count = post_count
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
            list_display = ('__repr__', 'posted_by', 'posted_at'),
            search_fields = ('message',)
        )
        
        # Order by the autoincrement id, rather than  posted_at, because
        # this matches the old system (in the old system editing a post 
        # would also cause its posted_at date to change, but not it's order,
        # and data for the original post date/time is now lost)
        ordering = ('id',) 
        

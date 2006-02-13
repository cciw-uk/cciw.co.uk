from django.db import models
from members import *
from polls import *

class Forum(models.Model):
    open = models.BooleanField("Open", default=True)
    location = models.CharField("Location/path", db_index=True, unique=True, maxlength=50)
    
    def get_absolute_url(self):
        return '/' + self.location
    
    def __repr__(self):
        return self.location

    class Meta:
        app_label = "cciw"   
        
    class Admin:
        pass

class NewsItem(models.Model):
    created_by = models.ForeignKey(Member, related_name="news_item_created")
    created_at = models.DateTimeField("Posted")
    summary = models.TextField("Summary")
    full_item = models.TextField("Full post", blank=True)
    subject = models.CharField("Subject", maxlength=100)
    
    def __repr__(self):
        return self.subject

    class Meta:
        app_label = "cciw"
        
    class Admin:
        pass

class Topic(models.Model):
    subject = models.CharField("Subject", maxlength=100)
    started_by = models.ForeignKey(Member, related_name="topic_started",
        verbose_name="started by")
    created_at = models.DateTimeField("Started", null=True)
    open = models.BooleanField("Open")
    hidden = models.BooleanField("Hidden")
    checked_by = models.ForeignKey(Member,
        null=True, blank=True, related_name="topic_checked",
        verbose_name="checked by")
    approved = models.BooleanField("Approved", null=True, blank=True)
    needs_approval = models.BooleanField("Needs approval", default=False)
    news_item = models.ForeignKey(NewsItem, null=True, blank=True,
        related_name="topic") # optional news item
    poll = models.ForeignKey(Poll, null=True, blank=True,
        related_name="topic") # optional topic
    forum = models.ForeignKey(Forum,
        related_name="topic")
    last_post_at = models.DateTimeField("Last post at", 
        null=True, blank=True) # needed for performance and simplicity in templates
    last_post_by = models.ForeignKey(Member, verbose_name="Last post by",
        null=True, blank=True) # needed for performance and simplicity in templates
    post_count = models.PositiveSmallIntegerField("Number of posts", default=0) # since we need 'lastPost', may as well have this too
        
    def __repr__(self):
        return  self.subject
        
    def get_absolute_url(self):
        return self.forum.get_absolute_url() + str(self.id) + '/'
    
    def get_link(self):
        return '<a href="' + self.get_absolute_url() + '">' + self.subject + '</a>'

    class Admin:
        list_display = ('subject', 'started_by', 'created_at')
        search_fields = ('subject',)
        
    class Meta:
        app_label = "cciw"
        ordering = ('-started_by',)

class Gallery(models.Model):
    location = models.CharField("Location/URL", maxlength=50)
    needs_approval = models.BooleanField("Photos need approval", default=False)

    def __repr__(self):
        return self.location
        
    def get_absolute_url(self):
        return '/' + self.location
        
    class Meta:
        app_label = "cciw"
        verbose_name_plural = "Galleries"
        ordering = ('-location',)
        
    class Admin:
        pass

class Photo(models.Model):
    created_at = models.DateTimeField("Started", null=True)
    open = models.BooleanField("Open")
    hidden = models.BooleanField("Hidden")
    filename = models.CharField("Filename", maxlength=50)
    description = models.CharField("Description", blank=True, maxlength=100)
    gallery = models.ForeignKey(Gallery,
        verbose_name="gallery",
        related_name="photo")
    checked_by = models.ForeignKey(Member,
        null=True, blank=True, related_name="checked_photo")
    approved = models.BooleanField("Approved", null=True, blank=True)
    needs_approval = models.BooleanField("Needs approval", default=False)
    last_post_at = models.DateTimeField("Last post at", 
        null=True, blank=True) # needed for performance and simplicity in templates
    last_post_by = models.ForeignKey(Member, verbose_name="Last post by",
        null=True, blank=True) # needed for performance and simplicity in templates
    post_count = models.PositiveSmallIntegerField("Number of posts", default=0) # since we need 'lastPost', may as well have this too

    def __repr__(self):
        return self.filename

    def get_absolute_url(self):
        return self.gallery.get_absolute_url() + str(self.id) + '/'

    class Meta:
        app_label = "cciw"
        
    class Admin:
        pass

class Post(models.Model):
    posted_by = models.ForeignKey(Member, 
        related_name="post")
    subject = models.CharField("Subject", maxlength=100) # deprecated, supports legacy boards
    message = models.TextField("Message")
    posted_at = models.DateTimeField("Posted at", null=True)
    hidden = models.BooleanField("Hidden", default=False)
    checked_by = models.ForeignKey(Member,
        verbose_name="checked by",
        null=True, blank=True, related_name="checked_post")
    approved = models.BooleanField("Approved", null=True)
    needs_approval = models.BooleanField("Needs approval", default=False)
    photo = models.ForeignKey(Photo, related_name="posts",
        null=True, blank=True)
    topic = models.ForeignKey(Topic, related_name="posts",
        null=True, blank=True)

    def __repr__(self):
        return "[" + str(self.id) + "]  " + self.message[:30]

    def updateParent(self, parent):
        "Update the cached info in the parent topic/photo"
        # Both types of parent, photos and topics,
        # are covered by this sub since they deliberately have the same
        # interface for this bit.
        post_count = parent.posts.count()
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
                
    def save(self):
        super(Post, self).save()
        # Update parent topic/photo
        
        if self.topic_id is not None:
            self.updateParent(self.topic)
            
        if self.photo_id is not None:
            self.updateParent(self.photo)
    
    class Meta:
        app_label = "cciw"
        # Order by the autoincrement id, rather than  posted_at, because
        # this matches the old system (in the old system editing a post 
        # would also cause its posted_at date to change, but not it's order,
        # and data for the original post date/time is now lost)
        ordering = ('id',) 

    class Admin:
        list_display = ('__repr__', 'posted_by', 'posted_at')
        search_fields = ('message',)
        

from django.db import models
from members import *
from polls import *
from datetime import datetime
from django.contrib.auth.models import User
import re
from django.conf import settings
import cciw.middleware.threadlocals as threadlocals
from django.template.defaultfilters import escape

# regex used to match forums that belong to camps
_camp_forum_re = re.compile('^' + settings.CAMP_FORUM_RE + '$')

class Forum(models.Model):
    open = models.BooleanField("Open", default=True)
    location = models.CharField("Location/path", db_index=True, unique=True, maxlength=50)
    
    def get_absolute_url(self):
        return '/' + self.location
    
    def __str__(self):
        return self.location
    
    def nice_name(self):
        m = _camp_forum_re.match(self.location)
        if m:
            captures = m.groupdict()
            number = captures['number']
            if number == 'all':
                return "forum for all camps, year %s" % captures['year']
            else:
                return "forum for camp %s, year %s" % (number, captures['year'])
        else:
            return "forum at %s" % self.location

    class Meta:
        app_label = "cciwmain"   
        
    class Admin:
        pass

class NewsItem(models.Model):
    created_by = models.ForeignKey(Member, related_name="news_item_created")
    created_at = models.DateTimeField("Posted")
    summary = models.TextField("Summary or short item, (bbcode)")
    full_item = models.TextField("Full post (HTML)", blank=True)
    subject = models.CharField("Subject", maxlength=100)
    
    def __str__(self):
        return self.subject

    @staticmethod
    def create_item(member, subject, short_item):
        """Create a news item with the correct defaults for a member."""
        return NewsItem(created_by=member,
                        created_at=datetime.now(),
                        summary=short_item,
                        full_item="",
                        subject=subject)

    class Meta:
        app_label = "cciwmain"
        
    class Admin:
        pass

class UserSpecificTopics(models.Manager):
    def get_query_set(self):
        queryset = super(UserSpecificTopics, self).get_query_set()
        user = threadlocals.get_current_user()
        if user is None or user.is_anonymous() or \
            not user.has_perm('cciwmain.edit_topic'):
            # Non-moderator user
            
            member = threadlocals.get_current_member()
            if member is not None:
                # include hidden topics by that user
                return (queryset.filter(started_by=member.user_name) | queryset.filter(hidden=False))
            else:
                return queryset.filter(hidden=False)
        else:
            return queryset

class Topic(models.Model):
    subject = models.CharField("Subject", maxlength=240)
    started_by = models.ForeignKey(Member, related_name="topic_started",
        verbose_name="started by")
    created_at = models.DateTimeField("Started", null=True)
    open = models.BooleanField("Open")
    hidden = models.BooleanField("Hidden", default=False)
    approved = models.BooleanField("Approved", null=True, blank=True)
    checked_by = models.ForeignKey(User,
        null=True, blank=True, related_name="topic_checked",
        verbose_name="checked by")
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
    
    # Managers:
    objects = UserSpecificTopics()
    all_objects = models.Manager()

    def __str__(self):
        return  self.subject
        
    def get_absolute_url(self):
        return self.forum.get_absolute_url() + str(self.id) + '/'
    
    def get_link(self):
        return '<a href="' + self.get_absolute_url() + '">' + escape(self.subject) + '</a>'

    @staticmethod
    def create_topic(member, subject, forum):
        """Create a topic with the correct defaults for a member"""
        return Topic(started_by=member,
                     subject=subject,
                     forum=forum,
                     created_at=datetime.now(),
                     hidden=(member.moderated == Member.MODERATE_ALL),
                     needs_approval=(member.moderated == Member.MODERATE_ALL),
                     open=True)

    class Admin:
        list_display = ('subject', 'started_by', 'created_at')
        search_fields = ('subject',)
    
    class Meta:
        app_label = "cciwmain"
        ordering = ('-started_by',)

class Gallery(models.Model):
    location = models.CharField("Location/URL", maxlength=50)
    needs_approval = models.BooleanField("Photos need approval", default=False)

    def __str__(self):
        return self.location
        
    def get_absolute_url(self):
        return '/' + self.location
        
    class Meta:
        app_label = "cciwmain"
        verbose_name_plural = "Galleries"
        ordering = ('-location',)
        
    class Admin:
        pass

class UserSpecificPhotos(models.Manager):
    def get_query_set(self):
        queryset = super(UserSpecificPhotos, self).get_query_set()
        user = threadlocals.get_current_user()
        if user is None or user.is_anonymous() or \
            not user.has_perm('cciwmain.edit_topic'):
            # Non-moderator user
            return queryset.filter(hidden=False)
        else:
            return queryset

class Photo(models.Model):
    created_at = models.DateTimeField("Started", null=True)
    open = models.BooleanField("Open")
    hidden = models.BooleanField("Hidden")
    filename = models.CharField("Filename", maxlength=50)
    description = models.CharField("Description", blank=True, maxlength=100)
    gallery = models.ForeignKey(Gallery,
        verbose_name="gallery",
        related_name="photo")
    checked_by = models.ForeignKey(User,
        null=True, blank=True, related_name="checked_photo")
    approved = models.BooleanField("Approved", null=True, blank=True)
    needs_approval = models.BooleanField("Needs approval", default=False)
    last_post_at = models.DateTimeField("Last post at", 
        null=True, blank=True) # needed for performance and simplicity in templates
    last_post_by = models.ForeignKey(Member, verbose_name="Last post by",
        null=True, blank=True) # needed for performance and simplicity in templates
    post_count = models.PositiveSmallIntegerField("Number of posts", default=0) # since we need 'lastPost', may as well have this too

    # managers
    objects = UserSpecificPhotos()
    all_objects = models.Manager()

    def __str__(self):
        return self.filename

    def get_absolute_url(self):
        return self.gallery.get_absolute_url() + str(self.id) + '/'

    class Meta:
        app_label = "cciwmain"
        
    class Admin:
        pass

class UserSpecificPosts(models.Manager):
    def get_query_set(self):
        """Return a filtered version of the queryset,
        appropriate for the current member/user."""
        queryset = super(UserSpecificPosts, self).get_query_set()
        user = threadlocals.get_current_user()
        if user is None or user.is_anonymous() or \
            not user.has_perm('cciwmain.edit_post'):
            # Non-moderator user
            
            member = threadlocals.get_current_member()
            if member is not None:
                # include hidden posts by that user
                return (queryset.filter(posted_by=member.user_name) | queryset.filter(hidden=False))
            else:
                return queryset.filter(hidden=False)
        else:
            return queryset

class Post(models.Model):
    posted_by = models.ForeignKey(Member, 
        related_name="posts")
    subject = models.CharField("Subject", maxlength=240, blank=True) # deprecated, supports legacy boards
    message = models.TextField("Message")
    posted_at = models.DateTimeField("Posted at", null=True)
    hidden = models.BooleanField("Hidden", default=False)
    approved = models.BooleanField("Approved", null=True)
    checked_by = models.ForeignKey(User,
        verbose_name="checked by",
        null=True, blank=True, related_name="checked_post")
    needs_approval = models.BooleanField("Needs approval", default=False)
    photo = models.ForeignKey(Photo, related_name="posts",
        null=True, blank=True)
    topic = models.ForeignKey(Topic, related_name="posts",
        null=True, blank=True)

    # Managers
    objects = UserSpecificPosts()
    all_objects = models.Manager()


    def __str__(self):
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

    def get_absolute_url(self):
        """Returns the absolte URL of the post that
        is always correct.  (This does a redirect to a URL that
        depends on the member viewing the page)"""
        return "/posts/%s/" % self.id

    def get_forum_url(self):
        """Gets the URL for the post in the context of its forum."""
        # Some posts are not visible to some users.  In a forum
        # thread, however, posts are always displayed in pages
        # of N posts, so the page a post is on depends on who is
        # looking at it.  This function takes this into account
        # and gives the correct URL.
        if self.topic_id is not None:
            thread = self.topic
        elif self.photo_id is not None:
            thread = self.photo
        # Post ordering is by id (for compatibility with legacy data)
        # The following uses the default manager so has permissions
        # built in.
        posts = thread.posts.filter(id__lt=self.id)
        previous_posts = posts.count()
        page = int(previous_posts/settings.FORUM_PAGINATE_POSTS_BY) + 1
        return "%s?page=%s#id%s" % (thread.get_absolute_url(), page, self.id)

    @staticmethod
    def create_post(member, message, topic=None, photo=None):
        """Creates a post with the correct defaults for a member."""
        post = Post(posted_by=member,
                    subject='',
                    message=message,
                    topic=topic,
                    photo=photo,
                    hidden=(member.moderated == Member.MODERATE_ALL),
                    needs_approval=(member.moderated == Member.MODERATE_ALL),
                    posted_at=datetime.now())
        return post
        
        
    class Meta:
        app_label = "cciwmain"
        # Order by the autoincrement id, rather than  posted_at, because
        # this matches the old system (in the old system editing a post 
        # would also cause its posted_at date to change, but not it's order,
        # and data for the original post date/time is now lost)
        ordering = ('id',) 

    class Admin:
        list_display = ('__str__', 'posted_by', 'posted_at')
        search_fields = ('message',)
        

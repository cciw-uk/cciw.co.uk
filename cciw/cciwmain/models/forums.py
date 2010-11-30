from django.db import models
from django.utils.safestring import mark_safe
from cciw.cciwmain.models.members import Member
from cciw.cciwmain.models.polls import Poll
from datetime import datetime
from django.contrib.auth.models import User
import re
from django.conf import settings
import cciw.middleware.threadlocals as threadlocals
from django.utils.html import escape

# regex used to match forums that belong to camps
_camp_forum_re = re.compile('^' + settings.CAMP_FORUM_RE + '$')

class Forum(models.Model):
    open = models.BooleanField("Open", default=True)
    location = models.CharField("Location/path", db_index=True, unique=True, max_length=50)

    def get_absolute_url(self):
        return '/' + self.location

    def __unicode__(self):
        return self.location

    def nice_name(self):
        m = _camp_forum_re.match(self.location)
        if m:
            captures = m.groupdict()
            number = captures['number']
            assert type(number) is unicode
            if number == u'all':
                return u"forum for all camps, year %s" % captures['year']
            else:
                return u"forum for camp %s, year %s" % (number, captures['year'])
        else:
            return u"forum at %s" % self.location


    class Meta:
        app_label = "cciwmain"

class NewsItem(models.Model):
    created_by = models.ForeignKey(Member, related_name="news_items_created")
    created_at = models.DateTimeField("Posted")
    summary = models.TextField("Summary or short item, (bbcode)")
    full_item = models.TextField("Full post (HTML)", blank=True)
    subject = models.CharField("Subject", max_length=100)

    def has_full_item(self):
        return len(self.full_item) > 0

    def __unicode__(self):
        return self.subject

    @staticmethod
    def create_item(member, subject, short_item):
        """
        Creates a news item with the correct defaults for a member.
        """
        return NewsItem.objects.create(created_by=member,
                                       created_at=datetime.now(),
                                       summary=short_item,
                                       full_item="",
                                       subject=subject)

    class Meta:
        app_label = "cciwmain"
        ordering = ('-created_at',)

class UserSpecificTopics(models.Manager):
    def get_query_set(self):
        queryset = super(UserSpecificTopics, self).get_query_set()
        user = threadlocals.get_current_user()
        if threadlocals.is_web_request() and \
           (user is None or user.is_anonymous() or \
            not user.has_perm('cciwmain.edit_topic')):
            # Non-moderator user
            member = threadlocals.get_current_member()
            if member is not None:
                # include hidden topics by that user
                return (queryset.filter(started_by=member) | queryset.filter(hidden=False))
            else:
                return queryset.filter(hidden=False)
        else:
            return queryset

class Topic(models.Model):
    subject = models.CharField("Subject", max_length=240)
    started_by = models.ForeignKey(Member, related_name="topics_started",
        verbose_name="started by")
    created_at = models.DateTimeField("Started", null=True)
    open = models.BooleanField("Open")
    hidden = models.BooleanField("Hidden", default=False)
    approved = models.NullBooleanField("Approved", blank=True)
    checked_by = models.ForeignKey(User,
        null=True, blank=True, related_name="topics_checked",
        verbose_name="checked by")
    needs_approval = models.BooleanField("Needs approval", default=False)
    news_item = models.ForeignKey(NewsItem, null=True, blank=True,
        related_name="topics") # optional news item
    poll = models.ForeignKey(Poll, null=True, blank=True,
        related_name="topics") # optional topic
    forum = models.ForeignKey(Forum, related_name="topics")

    # De-normalised fields needed for performance and simplicity in templates:
    last_post_at = models.DateTimeField("Last post at",
        null=True, blank=True)
    last_post_by = models.ForeignKey(Member, verbose_name="Last post by",
        null=True, blank=True, related_name='topics_with_last_post')
    # since we need 'last_post_by', may as well have this too:
    post_count = models.PositiveSmallIntegerField("Number of posts", default=0)

    # Managers:
    objects = UserSpecificTopics()
    all_objects = models.Manager()

    def __unicode__(self):
        return  u"Topic: " + self.subject

    def get_absolute_url(self):
        return self.forum.get_absolute_url() + str(self.id) + '/'

    def get_link(self):
        return mark_safe(u'<a href="%s">%s</a>' % (self.get_absolute_url(), escape(self.subject)))

    @staticmethod
    def create_topic(member, subject, forum, commit=True):
        """
        Creates a topic with the correct defaults for a member.
        It will be already saved unless 'commit' is False
        """
        topic = Topic(started_by=member,
                      subject=subject,
                      forum=forum,
                      created_at=datetime.now(),
                      hidden=(member.moderated == Member.MODERATE_ALL),
                      needs_approval=(member.moderated == Member.MODERATE_ALL),
                      open=True)
        if commit:
            topic.save()
        return topic

    class Meta:
        app_label = "cciwmain"
        ordering = ('-started_by',)

class Gallery(models.Model):
    location = models.CharField("Location/URL", max_length=50)
    needs_approval = models.BooleanField("Photos need approval", default=False)

    def __unicode__(self):
        return self.location

    def get_absolute_url(self):
        return '/' + self.location

    class Meta:
        app_label = "cciwmain"
        verbose_name_plural = "Galleries"
        ordering = ('-location',)

class UserSpecificPhotos(models.Manager):
    def get_query_set(self):
        queryset = super(UserSpecificPhotos, self).get_query_set()
        user = threadlocals.get_current_user()
        if threadlocals.is_web_request() and \
            (user is None or user.is_anonymous() or \
             not user.has_perm('cciwmain.edit_topic')):
            # Non-moderator user
            return queryset.filter(hidden=False)
        else:
            return queryset

class Photo(models.Model):
    created_at = models.DateTimeField("Started", null=True)
    open = models.BooleanField("Open")
    hidden = models.BooleanField("Hidden")
    filename = models.CharField("Filename", max_length=50)
    description = models.CharField("Description", blank=True, max_length=100)
    gallery = models.ForeignKey(Gallery,
        verbose_name="gallery",
        related_name="photos")
    checked_by = models.ForeignKey(User,
        null=True, blank=True, related_name="photos_checked")
    approved = models.NullBooleanField("Approved", blank=True)
    needs_approval = models.BooleanField("Needs approval", default=False)

    # De-normalised fields needed for performance and simplicity in templates:
    last_post_at = models.DateTimeField("Last post at",
        null=True, blank=True)
    last_post_by = models.ForeignKey(Member, verbose_name="Last post by",
        null=True, blank=True, related_name='photos_with_last_post')
    # since we need 'last_post_by', may as well have this too:
    post_count = models.PositiveSmallIntegerField("Number of posts", default=0)

    # managers
    objects = UserSpecificPhotos()
    all_objects = models.Manager()

    def __unicode__(self):
        return u"Photo: " + self.filename

    def get_absolute_url(self):
        return self.gallery.get_absolute_url() + str(self.id) + '/'

    @staticmethod
    def create_default_photo(filename, gallery):
        """
        Creates a (saved) photo with default attributes
        """
        return Photo.objects.create(
            created_at=datetime.now(),
            open=True,
            hidden=False,
            filename=filename,
            description="",
            gallery=gallery,
            checked_by=None,
            approved=None,
            needs_approval=False
        )

    class Meta:
        app_label = "cciwmain"

class UserSpecificPosts(models.Manager):
    def get_query_set(self):
        """Return a filtered version of the queryset,
        appropriate for the current member/user."""
        queryset = super(UserSpecificPosts, self).get_query_set()
        user = threadlocals.get_current_user()
        if threadlocals.is_web_request() and \
           (user is None or user.is_anonymous() or \
            not user.has_perm('cciwmain.edit_post')):
            # Non-moderator user

            member = threadlocals.get_current_member()
            if member is not None:
                # include hidden posts by that user
                return (queryset.filter(posted_by=member) | queryset.filter(hidden=False))
            else:
                return queryset.filter(hidden=False)
        else:
            return queryset

class Post(models.Model):
    posted_by = models.ForeignKey(Member,
        related_name="posts")
    subject = models.CharField("Subject", max_length=240, blank=True) # deprecated, supports legacy boards
    message = models.TextField("Message")
    posted_at = models.DateTimeField("Posted at", null=True)
    hidden = models.BooleanField("Hidden", default=False)
    approved = models.NullBooleanField("Approved")
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


    def __unicode__(self):
        return u"Post [%s]: %s" % (str(self.id), self.message[:30])

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

    def save(self, **kwargs):
        super(Post, self).save(**kwargs)
        # Update parent topic/photo

        if self.topic_id is not None:
            self.updateParent(self.topic)

        if self.photo_id is not None:
            self.updateParent(self.photo)

    def get_absolute_url(self):
        """Returns the absolute URL of the post that is always correct.
        (This does a redirect to a URL that depends on the member viewing the page)"""
        return "/posts/%s/" % self.id

    def get_forum_url(self):
        """Gets the URL for the post in the context of its forum."""
        # Some posts are not visible to some users.  In a forum
        # thread, however, posts are always displayed in pages
        # of N posts, so the page a post is on depends on who is
        # looking at it.  This function takes this into account
        # and gives the correct URL.  This is important for the case
        # or feed readers that won't in general be logged in as the
        # the user when they fetch the feed that may have absolute
        # URLs in it.
        # Also it's useful in case we change the paging.
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

    def is_parent_visible(self):
        if self.topic_id is not None:
            try:
                topic = self.topic
                return True
            except Topic.DoesNotExist:
                return False
        elif self.photo_id is not None:
            try:
                photo = self.photo
                return True
            except Photo.DoesNotExist:
                return False
        else:
            # no parent?
            return False

    @staticmethod
    def create_post(member, message, topic=None, photo=None):
        """
        Creates a (saved) post with the correct defaults for a member.
        """
        return Post.objects.create(posted_by=member,
                                   subject='',
                                   message=message,
                                   topic=topic,
                                   photo=photo,
                                   hidden=(member.moderated == Member.MODERATE_ALL),
                                   needs_approval=(member.moderated == Member.MODERATE_ALL),
                                   posted_at=datetime.now())

    class Meta:
        app_label = "cciwmain"
        # Order by the autoincrement id, rather than  posted_at, because
        # this matches the old system (in the old system editing a post
        # would also cause its posted_at date to change, but not it's order,
        # and data for the original post date/time is now lost)
        ordering = ('id',)

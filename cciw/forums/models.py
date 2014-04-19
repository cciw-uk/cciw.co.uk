from datetime import datetime, timedelta
import operator
import random
import re

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password, make_password

from django.core import mail
from django.db import models
from django.utils.html import escape
from django.utils.safestring import mark_safe
from cciw.cciwmain import common
from cciw.middleware import threadlocals

# regex used to match forums that belong to camps
_camp_forum_re = re.compile('^' + settings.CAMP_FORUM_RE + '$')


class Permission(models.Model):
    POLL_CREATOR = "Poll creator"
    NEWS_CREATOR = "News creator"

    id = models.PositiveSmallIntegerField("ID", primary_key=True)
    description = models.CharField("Description", max_length=40)

    def __str__(self):
        return self.description

    class Meta:
        ordering = ('id',)


class UserSpecificMembers(models.Manager):

    def get_queryset(self):
        user = threadlocals.get_current_user()
        if threadlocals.is_web_request() and \
           (user is None or user.is_anonymous() or not user.is_staff or \
            not user.has_perm('cciwmain.change_member')):
            return super(UserSpecificMembers, self).get_queryset().filter(hidden=False)
        else:
            return super(UserSpecificMembers, self).get_queryset()

    def get_by_natural_key(self, user_name):
        return self.get(user_name=user_name)


class Member(models.Model):
    """Represents a user of the CCIW message boards."""
    MESSAGES_NONE = 0
    MESSAGES_WEBSITE = 1
    MESSAGES_EMAIL = 2
    MESSAGES_EMAIL_AND_WEBSITE = 3

    MODERATE_OFF = 0
    MODERATE_NOTIFY = 1
    MODERATE_ALL = 2

    MESSAGE_OPTIONS = (
        (MESSAGES_NONE,     u"Don't allow messages"),
        (MESSAGES_WEBSITE,  u"Store messages on the website"),
        (MESSAGES_EMAIL,    u"Send messages via email"),
        (MESSAGES_EMAIL_AND_WEBSITE, u"Store messages and send via email")
    )

    MODERATE_OPTIONS = (
        (MODERATE_OFF,      u"Off"),
        (MODERATE_NOTIFY,   u"Unmoderated, but notify"),
        (MODERATE_ALL,      u"Fully moderated")
    )

    user_name   = models.CharField("User name", max_length=30, unique=True)
    real_name   = models.CharField("'Real' name", max_length=30, blank=True)
    email       = models.EmailField("Email address")
    password    = models.CharField("Password", max_length=255)
    date_joined = models.DateTimeField("Date joined", null=True)
    last_seen   = models.DateTimeField("Last on website", null=True)
    show_email  = models.BooleanField("Make email address visible", default=False)
    message_option = models.PositiveSmallIntegerField("Message storing",
        choices=MESSAGE_OPTIONS, default=1)
    comments    = models.TextField("Comments", blank=True)
    moderated   = models.PositiveSmallIntegerField("Moderated", default=0,
        choices=MODERATE_OPTIONS)
    hidden      = models.BooleanField("Hidden", default=False)
    banned      = models.BooleanField("Banned", default=False)
    permissions = models.ManyToManyField(Permission,
        verbose_name="permissions", related_name="member_with_permission",
        blank=True, null=True)
    icon         = models.ImageField("Icon", upload_to=settings.MEMBER_ICON_UPLOAD_PATH, blank=True)
    dummy_member = models.BooleanField("Dummy member status", default=False) # supports ancient posts in message boards

    # Managers
    objects = UserSpecificMembers()
    all_objects = models.Manager()

    def __str__(self):
        return self.user_name

    def natural_key(self):
        return self.user_name

    def get_absolute_url(self):
        if self.dummy_member:
            return None
        else:
            return common.get_member_href(self.user_name)

    def get_link(self):
        if self.dummy_member:
            return self.user_name
        else:
            return common.get_member_link(self.user_name)

    def get_icon(self):
        user_name = self.user_name.strip()
        if user_name.startswith(u"'"): # dummy user
            return u''
        else:
            return mark_safe(u'<img src="%s%s/%s.png" class="userIcon" alt="icon" />'
                             % (settings.MEDIA_URL, settings.MEMBER_ICON_PATH, user_name))

    def new_messages(self):
        return self.messages_received.filter(box=Message.MESSAGE_BOX_INBOX).count()

    def saved_messages(self):
        return self.messages_received.filter(box=Message.MESSAGE_BOX_SAVED).count()

    def has_perm(self, perm):
        """Does the member has the specified permission?
        perm is one of the permission constants in Permission."""
        return len(self.permissions.filter(description=perm)) > 0

    @property
    def can_add_news(self):
        return self.has_perm(Permission.NEWS_CREATOR)

    @property
    def can_add_poll(self):
        return self.has_perm(Permission.POLL_CREATOR)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        """
        Returns a boolean of whether the raw_password was correct. Handles
        hashing formats behind the scenes.
        """
        def setter(raw_password):
            self.set_password(raw_password)
            self.save(update_fields=["password"])
        return check_password(raw_password, self.password, setter)

    # For the sake of django.contrib.auth.tokens.PasswordResetTokenGenerator
    @property
    def last_login(self):
        return self.last_seen if self.last_seen else datetime(1970,1,1)

    class Meta:
        ordering = ('user_name',)


class Award(models.Model):
    name = models.CharField("Award name", max_length=50)
    value = models.SmallIntegerField("Value")
    year = models.PositiveSmallIntegerField("Year")
    description = models.CharField("Description", max_length=200)
    image = models.ImageField("Award image",
        upload_to=settings.AWARD_UPLOAD_PATH)

    def __str__(self):
        return u"%s %s" % (self.name, self.year)

    def nice_name(self):
        return str(self)

    def imageurl(self):
        return self.image.url

    def get_absolute_url(self):
        from django.template.defaultfilters import slugify
        from django.core.urlresolvers import reverse
        return reverse('cciw.forums.views.awards.index') + "#" + slugify(str(self))

    class Meta:
        ordering = ('-year', 'name',)


class PersonalAwardManager(models.Manager):

    def get_queryset(self, *args, **kwargs):
        qs = super(PersonalAwardManager, self).get_queryset(*args, **kwargs)
        return qs.select_related('member')


class PersonalAward(models.Model):
    reason = models.CharField("Reason for award", max_length=200)
    date_awarded = models.DateField("Date awarded", null=True, blank=True)
    award = models.ForeignKey(Award,
        verbose_name="award",
        related_name="personal_awards")
    member = models.ForeignKey(Member,
        verbose_name="member",
        related_name="personal_awards")

    objects = PersonalAwardManager()

    def __str__(self):
        return "%s to %s" % (self.award.name, self.member.user_name)

    class Meta:
        ordering = ('date_awarded',)


class Message(models.Model):
    MESSAGE_BOX_INBOX = 0
    MESSAGE_BOX_SAVED = 1

    MESSAGE_BOXES = (
        (MESSAGE_BOX_INBOX, "Inbox"),
        (MESSAGE_BOX_SAVED, "Saved")
    )
    from_member = models.ForeignKey(Member,
        verbose_name="from member",
        related_name="messages_sent"
    )
    to_member = models.ForeignKey(Member,
        verbose_name="to member",
        related_name="messages_received")
    time = models.DateTimeField("At")
    text = models.TextField("Message")
    box = models.PositiveSmallIntegerField("Message box",
        choices=MESSAGE_BOXES)

    @staticmethod
    def send_message(to_member, from_member, text):
        if to_member.message_option == Member.MESSAGES_NONE:
            return
        if to_member.message_option != Member.MESSAGES_EMAIL:
            msg = Message(to_member=to_member, from_member=from_member,
                        text=text, time=datetime.now(),
                        box=Message.MESSAGE_BOX_INBOX)
            msg.save()
        if to_member.message_option != Member.MESSAGES_WEBSITE:
            mail.send_mail("Message on cciw.co.uk",
"""You have received a message on cciw.co.uk from user %(from)s:

%(message)s
----
You can view your inbox here:
https://%(domain)s/members/%(to)s/messages/inbox/

You can reply here:
https://%(domain)s/members/%(from)s/messages/

""" % {'from': from_member.user_name, 'to': to_member.user_name,
        'domain': common.get_current_domain(), 'message': text},
        settings.SERVER_EMAIL, [to_member.email])
        return msg


    def __str__(self):
        return u"[%s] to %s from %s" % (self.id, self.to_member, self.from_member)

    class Meta:
        ordering = ('-time',)


VOTING_RULES = (
    (0, u"Unlimited"),
    (1, u"'X' votes per member"),
    (2, u"'X' votes per member per day")
)


class Poll(models.Model):
    UNLIMITED = 0
    X_VOTES_PER_USER = 1
    X_VOTES_PER_USER_PER_DAY = 2

    title = models.CharField("Title", max_length=100)
    intro_text = models.CharField("Intro text", max_length=400, blank=True)
    outro_text = models.CharField("Closing text", max_length=400, blank=True)
    voting_starts = models.DateTimeField("Voting starts")
    voting_ends = models.DateTimeField("Voting ends")
    rules = models.PositiveSmallIntegerField("Rules",
        choices=VOTING_RULES)
    rule_parameter = models.PositiveSmallIntegerField("Parameter for rule",
        default=1)
    have_vote_info = models.BooleanField("Full vote information available",
        default=True)
    created_by = models.ForeignKey(Member, verbose_name="created by",
        related_name="polls_created")

    def __str__(self):
        return self.title

    def can_vote(self, member):
        """Returns true if member can vote on the poll"""
        if not self.can_anyone_vote():
            return False
        if not self.have_vote_info:
            # Can't calculate this, but it will only happen
            # for legacy polls, which are all closed.
            return True
        if self.rules == Poll.UNLIMITED:
            return True
        queries = [] # queries representing users relevant votes
        for po in self.poll_options.all():
            if self.rules == Poll.X_VOTES_PER_USER:
                queries.append(po.votes.filter(member=member.pk))
            elif self.rules == Poll.X_VOTES_PER_USER_PER_DAY:
                queries.append(po.votes.filter(member=member.pk,
                                                date__gte=datetime.now() - timedelta(1)))
        # combine them all and do an SQL count.
        if len(queries) == 0:
            return False # no options to vote on!
        count = reduce(operator.or_, queries).count()
        if count >= self.rule_parameter:
            return False
        else:
            return True

    def total_votes(self):
        return self.poll_options.all().aggregate(models.Sum('total'))['total__sum']

    def can_anyone_vote(self):
        return (self.voting_ends > datetime.now()) and \
            (self.voting_starts < datetime.now())

    def verbose_rules(self):
        if self.rules == Poll.UNLIMITED:
            return u"Unlimited number of votes."
        elif self.rules == Poll.X_VOTES_PER_USER:
            return u"%s vote(s) per user." % self.rule_parameter
        elif self.rules == Poll.X_VOTES_PER_USER_PER_DAY:
            return u"%s vote(s) per user per day." % self.rule_parameter

    class Meta:
        ordering = ('title',)


class PollOption(models.Model):
    text = models.CharField("Option text", max_length=200)
    total = models.PositiveSmallIntegerField("Number of votes")
    poll = models.ForeignKey(Poll, verbose_name="Associated poll",
        related_name="poll_options")
    listorder = models.PositiveSmallIntegerField("Order in list")

    def __str__(self):
        return self.text

    def percentage(self):
        """
        Get the percentage of votes this option got
        compared to the total number of votes in the whole. Return
        'n/a' if total votes = 0
        """
        sum = self.poll.total_votes()
        if sum == 0:
            return 'n/a'
        else:
            if self.total == 0:
                return '0%'
            else:
                return '%.1f' % (float(self.total)/sum*100) + '%'

    def bar_width(self):
        sum = self.poll.total_votes()
        if sum == 0:
            return 0
        else:
            return int(float(self.total)/sum*300)

    class Meta:
        ordering = ('poll', 'listorder',)


class VoteInfo(models.Model):
    poll_option = models.ForeignKey(PollOption,
        related_name="votes")
    member = models.ForeignKey(Member,
        verbose_name="member",
        related_name="poll_votes")
    date = models.DateTimeField("Date")

    def save(self):
        # Manually update the parent
        #  - this is the easiest way for vote counts to work
        #    with legacy polls that don't have VoteInfo objects
        is_new = (self.id is None)
        super(VoteInfo, self).save()
        if is_new:
            self.poll_option.total += 1
        self.poll_option.save()


class Forum(models.Model):
    open = models.BooleanField("Open", default=True)
    location = models.CharField("Location/path", db_index=True, unique=True, max_length=50)

    def get_absolute_url(self):
        return '/' + self.location

    def __str__(self):
        return self.location

    def nice_name(self):
        m = _camp_forum_re.match(self.location)
        if m:
            captures = m.groupdict()
            number = captures['number']
            assert type(number) is str
            if number == u'all':
                return u"forum for all camps, year %s" % captures['year']
            else:
                return u"forum for camp %s, year %s" % (number, captures['year'])
        else:
            return u"forum at %s" % self.location


class NewsItem(models.Model):
    created_by = models.ForeignKey(Member, related_name="news_items_created")
    created_at = models.DateTimeField("Posted")
    summary = models.TextField("Summary or short item, (bbcode)")
    full_item = models.TextField("Full post (HTML)", blank=True)
    subject = models.CharField("Subject", max_length=100)

    def has_full_item(self):
        return len(self.full_item) > 0

    def __str__(self):
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
        ordering = ('-created_at',)


class UserSpecificTopics(models.Manager):
    def get_queryset(self):
        queryset = super(UserSpecificTopics, self).get_queryset()
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
    open = models.BooleanField("Open", default=False)
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

    def __str__(self):
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
        ordering = ('-started_by',)


class Gallery(models.Model):
    location = models.CharField("Location/URL", max_length=50)
    needs_approval = models.BooleanField("Photos need approval", default=False)

    def __str__(self):
        return self.location

    def get_absolute_url(self):
        return '/' + self.location

    class Meta:
        verbose_name_plural = "Galleries"
        ordering = ('-location',)


class UserSpecificPhotos(models.Manager):
    def get_queryset(self):
        queryset = super(UserSpecificPhotos, self).get_queryset()
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
    open = models.BooleanField("Open", default=False)
    hidden = models.BooleanField("Hidden", default=False)
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

    def __str__(self):
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


class UserSpecificPosts(models.Manager):
    def get_queryset(self):
        """Return a filtered version of the queryset,
        appropriate for the current member/user."""
        queryset = super(UserSpecificPosts, self).get_queryset()
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


    def __str__(self):
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
                return not self.topic.hidden
            except Topic.DoesNotExist:
                return False
        elif self.photo_id is not None:
            try:
                return not self.photo.hidden
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
        # Order by the autoincrement id, rather than  posted_at, because
        # this matches the old system (in the old system editing a post
        # would also cause its posted_at date to change, but not it's order,
        # and data for the original post date/time is now lost)
        ordering = ('id',)

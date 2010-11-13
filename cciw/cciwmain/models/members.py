from django.db import models
from django.conf import settings
from django.core import mail
from cciw.middleware import threadlocals
from cciw.cciwmain import utils
from datetime import datetime
from cciw.cciwmain.utils import get_member_link, get_member_href

import os

class Permission(models.Model):
    POLL_CREATOR = "Poll creator"
    NEWS_CREATOR = "News creator"

    id = models.PositiveSmallIntegerField("ID", primary_key=True)
    description = models.CharField("Description", max_length=40)

    def __unicode__(self):
        return self.description

    class Meta:
        ordering = ('id',)
        app_label = "cciwmain"

class UserSpecificMembers(models.Manager):
    def get_query_set(self):
        user = threadlocals.get_current_user()
        if threadlocals.is_web_request() and \
           (user is None or user.is_anonymous() or not user.is_staff or \
            not user.has_perm('cciwmain.change_member')):
            return super(UserSpecificMembers, self).get_query_set().filter(hidden=False)
        else:
            return super(UserSpecificMembers, self).get_query_set()

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

    # We use a string primary key because we know that user_names can't change,
    # and for database efficiency -- we can generate a link to a member's page
    # just using the primary key, so for other tables that refer to Member,
    # (e.g. Post) we don't need to hit the database again.  However,
    # improvements to QuerySet.select_related() probably mean that this isn't
    # necessary anymore.
    user_name   = models.CharField("User name", primary_key=True, max_length=30, editable=False)
    real_name   = models.CharField("'Real' name", max_length=30, blank=True)
    email       = models.EmailField("Email address")
    password    = models.CharField("Password", max_length=30)
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

    def __unicode__(self):
        return self.user_name

    def get_absolute_url(self):
        if self.dummy_member:
            return None
        else:
            return get_member_href(self.user_name)

    def get_link(self):
        if self.dummy_member:
            return self.user_name
        else:
            return get_member_link(self.user_name)

    def check_password(self, plaintextPass):
        """Checks a password is correct"""
        import crypt
        return crypt.crypt(plaintextPass, self.password) == self.password

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

    @staticmethod
    def generate_salt():
        import random, datetime
        rand64= "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        random.seed(datetime.datetime.today().microsecond)
        return rand64[int(random.random()*64)] + rand64[int(random.random()*64)]

    @staticmethod
    def encrypt_password(memberPass):
        import crypt
        """Encrypt a members password"""
        # written to maintain compatibility with existing password file
        return crypt.crypt(memberPass, Member.generate_salt())

    class Meta:
        ordering = ('user_name',)
        app_label = "cciwmain"

class Award(models.Model):
    name = models.CharField("Award name", max_length=50)
    value = models.SmallIntegerField("Value")
    year = models.PositiveSmallIntegerField("Year")
    description = models.CharField("Description", max_length=200)
    image = models.ImageField("Award image",
        upload_to=settings.AWARD_UPLOAD_PATH)

    def __unicode__(self):
        return self.name + u" " + unicode(self.year)

    def nice_name(self):
        return str(self)

    def imageurl(self):
        return self.image.url

    def get_absolute_url(self):
        from django.template.defaultfilters import slugify
        return "/awards/#" + slugify(unicode(self))

    class Meta:
        app_label = "cciwmain"
        ordering = ('-year', 'name',)

class PersonalAward(models.Model):
    reason = models.CharField("Reason for award", max_length=200)
    date_awarded = models.DateField("Date awarded", null=True, blank=True)
    award = models.ForeignKey(Award,
        verbose_name="award",
        related_name="personal_awards")
    member = models.ForeignKey(Member,
        verbose_name="member",
        related_name="personal_awards")

    def __unicode__(self):
        return "%s to %s" % (self.award.name, self.member.user_name)

    class Meta:
        app_label = "cciwmain"
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
        'domain': utils.get_current_domain(), 'message': text},
        "website@cciw.co.uk", [to_member.email])


    def __unicode__(self):
        return u"[%s] to %s from %s" % (unicode(self.id), unicode(self.to_member), unicode(self.from_member))

    class Meta:
        app_label = "cciwmain"
        ordering = ('-time',)

from django.db import models
from cciw.cciwmain.settings import *

class Permission(models.Model):
    SUPERUSER = 1
    USER_MODERATOR = 2
    POST_MODERATOR =  3
    PHOTO_APPROVER = 4
    POLL_CREATOR = 5
    NEWS_CREATOR = 6
    AWARD_CREATOR = 7

    id = models.PositiveSmallIntegerField("ID", primary_key=True)
    description = models.CharField("Description", maxlength=40)
    
    def __repr__(self):
        return self.description
    
    class Meta:
        ordering = ('id',)
        app_label = "cciwmain"
        
    class Admin:
        pass

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
        (MESSAGES_NONE,     "Don't allow messages"),
        (MESSAGES_WEBSITE,  "Store messages on the website"),
        (MESSAGES_EMAIL,    "Send messages via email"),
        (MESSAGES_EMAIL_AND_WEBSITE, "Store messages and send via email")
    )
    
    MODERATE_OPTIONS = (
        (MODERATE_OFF,      "Off"),
        (MODERATE_NOTIFY,   "Unmoderated, but notify"),
        (MODERATE_ALL,      "Fully moderated")
    )

    user_name   = models.CharField("User name", primary_key=True, maxlength=30)
    real_name   = models.CharField("Real name", maxlength=30, blank=True)
    email       = models.EmailField("Email address")
    password    = models.CharField("Password", maxlength=30)
    date_joined = models.DateTimeField("Date joined", null=True)
    last_seen   = models.DateTimeField("Last on website", null=True)
    show_email  = models.BooleanField("Show email address", default=False)
    message_option = models.PositiveSmallIntegerField("Message option",
        choices=MESSAGE_OPTIONS, default=1)
    comments    = models.TextField("Comments", blank=True)
    confirmed   = models.BooleanField("Confirmed", default=False)
    confirm_secret = models.CharField("Confirmation secret", maxlength=30, blank=True)
    moderated   = models.PositiveSmallIntegerField("Moderated", default=0,
        choices=MODERATE_OPTIONS)
    hidden      = models.BooleanField("Hidden", default=False)
    banned      = models.BooleanField("Banned", default=False)
    new_email   = models.EmailField("New email address (unconfirmed)", blank=True)
    bookmarks_notify = models.BooleanField("Bookmark notifcations enabled", default=False)
    permissions = models.ManyToManyField(Permission,
        verbose_name="permissions", related_name="member_with_permission",
        blank=True, null=True, filter_interface=models.HORIZONTAL)
    icon          = models.ImageField("Icon", upload_to=MEMBERS_ICONS_UPLOAD_PATH, blank=True)
    dummy_member = models.BooleanField("Dummy member status", default=False) # supports ancient posts in message boards
        
    def __repr__(self):
        return self.user_name
        
    def get_absolute_url(self):
        return "/members/" + self.user_name + "/"
        
    def get_link(self):
        from cciw.cciwmain.utils import get_member_link
        if self.dummy_member:
            return self.user_name
        else:
            return get_member_link(self.user_name)

    def icon_image(self):
        from cciw.cciwmain.settings import CCIW_MEDIA_ROOT
        "Get an HTML image with the member's icon"
        if self.icon and len(self.icon) > 0:
            return '<img src="' + CCIW_MEDIA_ROOT + 'images/members/' + self.icon + '" class="userIcon" alt="icon" />'
        else:
            return ''

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
        for p in self.permissions:
            if p.id == perm or p.id == Permission.SUPERUSER:
                return True
        return False

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
        
    class Admin:
        search_fields = (
            'user_name', 'real_name', 'email'
        )
        list_display = (
            'user_name', 'real_name', 'email', 'date_joined'
        )
        list_filter = (
            'dummy_member',
            'hidden',
            'banned',
            'moderated',
            'confirmed',
        )

class Award(models.Model):
    name = models.CharField("Award name", maxlength=50)
    value = models.SmallIntegerField("Value")
    year = models.PositiveSmallIntegerField("Year")
    description = models.CharField("Description", maxlength=200)
    image = models.ImageField("Award image", 
        upload_to = AWARD_UPLOAD_PATH)

    def __repr__(self):
        return self.name + " " + str(self.year)
        
    def nice_name(self):
        return repr(self)
    
    def imageurl(self):
        from cciw.cciwmain.settings import CCIW_MEDIA_ROOT
        return CCIW_MEDIA_ROOT + "images/awards/" + self.image
        
    def get_absolute_url(self):
        from django.template.defaultfilters import slugify
        return "/awards/#" + slugify(repr(self))
    
    class Meta:
        app_label = "cciwmain"
        ordering = ('-year', 'name',)
    
    class Admin:
        list_display = ('name', 'year')
    
class PersonalAward(models.Model):
    reason = models.CharField("Reason for award", maxlength=200)
    date_awarded = models.DateField("Date awarded", null=True, blank=True)
    award = models.ForeignKey(Award,
        verbose_name="award", 
        related_name="personal_awards")
    member = models.ForeignKey(Member,
        verbose_name="member",
        related_name="personal_awards")
        
    def __repr__(self):
        return self.award.name + " to " + self.member.user_name
        
        
    class Meta:
        app_label = "cciwmain"   
        ordering = ('date_awarded',)

    class Admin:
        list_display = ('award', 'member','reason', 'date_awarded')
        
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
    
    def __repr__(self):
        return "[" + str(self.id) + "] to " + repr(self.to_member)  + " from " + repr(self.from_member)
    
    class Meta:
        app_label = "cciwmain"
        ordering = ('-time',)
    
    class Admin:
        list_display = ('to_member', 'from_member', 'time')

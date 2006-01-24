from django.db import models
from cciw.apps.cciw.settings import *

class Permission(models.Model):
    id = meta.PositiveSmallIntegerField("ID", primary_key=True)
    description = meta.CharField("Description", maxlength=40)
    
    def __repr__(self):
        return self.description
    
    class META:
        admin = meta.Admin()
        ordering = ('id',)
        # Permissions table will be filled with data
        # that correspond to the constants below
        module_constants = {
            'SUPERUSER': 1,
            'USER_MODERATOR': 2,
            'POST_MODERATOR': 3,
            'PHOTO_APPROVER': 4,
            'POLL_CREATOR': 5,
            'NEWS_CREATOR': 6,
            'AWARD_CREATOR': 7
        }
    

MESSAGE_OPTIONS = (
    (0, "Don't allow messages"),
    (1, "Store messages on the website"),
    (2, "Send messages via email"),
    (3, "Store messages and send via email")
)

MODERATE_OPTIONS = (
    (0, "Off"),
    (1, "Unmoderated, but notify"),
    (2, "Fully moderated")
)

class Member(models.Model):
    user_name   = meta.CharField("User name", primary_key=True, maxlength=30)
    real_name   = meta.CharField("Real name", maxlength=20, blank=True)
    email      = meta.EmailField("Email address")
    password   = meta.CharField("Password", maxlength=30)
    date_joined = meta.DateTimeField("Date joined", null=True)
    last_seen   = meta.DateTimeField("Last on website", null=True)
    show_email  = meta.BooleanField("Show email address", default=False)
    message_option = meta.PositiveSmallIntegerField("Message option",
        choices = MESSAGE_OPTIONS, default=1)
    comments   = meta.TextField("Comments", blank=True)
    confirmed  = meta.BooleanField("Confirmed", default=False)
    confirm_secret = meta.CharField("Confirmation secret", maxlength=30, blank=True)
    moderated  = meta.PositiveSmallIntegerField("Moderated", default=0,
            choices = MODERATE_OPTIONS)
    hidden     = meta.BooleanField("Hidden", default=False)
    banned     = meta.BooleanField("Banned", default=False)
    new_email   = meta.EmailField("New email address (unconfirmed)", blank=True)
    bookmarks_notify = meta.BooleanField("Bookmark notifcations enabled", default=False)
    permissions = meta.ManyToManyField(Permission,
        verbose_name="permissions",
        related_name="member_with_permission",
        blank=True,
        null=True)
    icon          = meta.ImageField("Icon", upload_to = MEMBERS_ICONS_UPLOAD_PATH, blank=True)
    dummy_member = meta.BooleanField("Dummy member status", default=False) # supports ancient posts in message boards
        
    def __repr__(self):
        return self.user_name
        
    def get_absolute_url(self):
        return "/members/" + self.user_name + "/"
        
    def get_link(self):
        from cciw.apps.cciw.utils import get_member_link
        if self.dummy_member:
            return self.user_name
        else:
            return get_member_link(self.user_name)

    def icon_image(self):
        from cciw.apps.cciw.settings import CCIW_MEDIA_ROOT
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
        from django.models.members import messages
        return self.get_message_received_count(box__exact=messages.MESSAGE_BOX_INBOX)

    def saved_messages(self):
        from django.models.members import messages
        return self.get_message_received_count(box__exact=messages.MESSAGE_BOX_SAVED)
        
    def _module_generate_salt():
        import random, datetime
        rand64= "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        random.seed(datetime.datetime.today().microsecond)
        return rand64[int(random.random()*64)] + rand64[int(random.random()*64)]
    
    def _module_encrypt_password(memberPass):
        import crypt
        """Encrypt a members password"""
        # written to maintain compatibility with existing password file
        return crypt.crypt(memberPass, generate_salt())

    class META:
        admin = meta.Admin(
            search_fields = (
                'user_name', 'real_name', 'email'
            ),
            list_display = (
                'user_name', 'real_name', 'email', 'date_joined'
            ),
            list_filter = (
                'dummy_member',
                'hidden',
                'banned',
                'moderated',
                'confirmed',
            )
            
        )
        module_constants = {
            'MESSAGES_NONE': 0,
            'MESSAGES_WEBSITE': 1,
            'MESSAGES_EMAIL' : 2,
            'MESSAGES_EMAIL_AND_WEBSITE': 3,
            'MODERATE_OFF': 0,
            'MODERATE_NOTIFY': 1,
            'MODERATE_ALL': 2
        }
        ordering = ('user_name',)
        

class Award(models.Model):
    name = meta.CharField("Award name", maxlength=50)
    year = meta.PositiveSmallIntegerField("Year")
    description = meta.CharField("Description", maxlength=200)
    image = meta.ImageField("Award image", 
        upload_to = AWARD_UPLOAD_PATH)

    def __repr__(self):
        return self.name + " " + str(self.year)
        
    def nice_name(self):
        return repr(self)
    
    def imageurl(self):
        from cciw.apps.cciw.settings import CCIW_MEDIA_ROOT
        return CCIW_MEDIA_ROOT + "images/awards/" + self.image
        
    def get_absolute_url(self):
        from django.core.template.defaultfilters import slugify
        return "/awards/#" + slugify(repr(self))
    
    class META:
        admin = meta.Admin(
            list_display = ('name','year'),
        )
        ordering = ('-year', 'name',)
        
    
class PersonalAward(models.Model):
    reason = meta.CharField("Reason for award", maxlength=200)
    date_awarded = meta.DateField("Date awarded", null=True, blank=True)
    award = meta.ForeignKey(Award,
        verbose_name="award", 
        related_name="personal_award")
    member = meta.ForeignKey(Member,
        verbose_name="member",
        related_name="personal_award")
        
    def __repr__(self):
        return self.get_award().name + " to " + self.get_member().user_name
        
        
    class META:
        admin = meta.Admin(
            list_display = ('award', 'member','reason', 'date_awarded')
        )
        ordering = ('date_awarded',)

BOOKMARK_CATEGORIES = (
    (0, "Often visited"),
    (1, "Classics")
)

class Bookmark(models.Model):
    url = meta.CharField("URL", maxlength="60") # 60?
    title = meta.CharField("Title", maxlength="50") # 100?
    member = meta.ForeignKey(Member, verbose_name="member",
        related_name="bookmark")
    last_updated = meta.DateTimeField("Last updated",
        null=True, blank=True)
    last_seen = meta.DateTimeField("Last seen",
        null=True, blank=True)
    public = meta.BooleanField("Public")
    category = meta.PositiveSmallIntegerField("Category", choices = BOOKMARK_CATEGORIES)
    
    def __repr__(self):
        return self.title

    class META:
        admin = meta.Admin()
        ordering = ('category', '-last_updated')
    
MESSAGE_BOXES = (
    (0, "Inbox"),
    (1, "Saved")
)

class Message(models.Model):
    from_member = meta.ForeignKey(Member,
        verbose_name="from member",
        related_name="message_sent"
    )
    to_member = meta.ForeignKey(Member, 
        verbose_name="to member",
        related_name="message_received")
    time = meta.DateTimeField("At")
    text = meta.TextField("Message")
    box = meta.PositiveSmallIntegerField("Message box",
        choices = MESSAGE_BOXES)
    
    def __repr__(self):
        #return str(self.id)
        return "[" + str(self.id) + "] to " + repr(self.get_to_member())  + " from " + repr(self.get_from_member())
    
    class META:
        admin = meta.Admin(
            list_display = ('to_member', 'from_member', 'time')
        )
        ordering = ('-time',)
        module_constants = {
            'MESSAGE_BOX_INBOX': 0,
            'MESSAGE_BOX_SAVED': 1
        }

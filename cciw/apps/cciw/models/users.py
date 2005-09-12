from django.core import meta
from cciw.apps.cciw.settings import *

class Permission(meta.Model):
	id = meta.PositiveSmallIntegerField("ID", primary_key=True)
	description = meta.CharField("Description", maxlength=40)
	
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
	
	def __repr__(self):
		return self.description

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

class User(meta.Model):
	userName   = meta.CharField("User name", maxlength=30, db_index=True, unique=True)
	realName   = meta.CharField("Real name", maxlength=20, blank=True)
	email      = meta.EmailField("Email address")
	password   = meta.CharField("Password", maxlength=30)
	dateJoined = meta.DateTimeField("Date joined", null=True)
	lastSeen   = meta.DateTimeField("Last on website", null=True)
	showEmail  = meta.BooleanField("Show email address", default=False)
	messageOption = meta.PositiveSmallIntegerField("Message option",
		choices = MESSAGE_OPTIONS)
	comments   = meta.TextField("Comments", blank=True)
	confirmed  = meta.BooleanField("Confirmed", default=False)
	confirmSecret = meta.CharField("Confirmation secret", maxlength=30, blank=True)
	moderated  = meta.PositiveSmallIntegerField("Moderated",
		choices = MODERATE_OPTIONS)
	hidden     = meta.BooleanField("Hidden", default=False)
	banned     = meta.BooleanField("Banned", default=False)
	newEmail   = meta.EmailField("New email address (unconfirmed)", blank=True)
	bookmarksNotify = meta.BooleanField("Bookmark notifcations enabled", default=False)
	publicBookmarks = meta.BooleanField("Bookmarks are public", default=True)
	permissions = meta.ManyToManyField(Permission,
		verbose_name="permissions",
		related_name="userWithPermission",
		blank=True,
		null=True)
	dummyUser = meta.BooleanField("Is dummy user", default=False) # supports ancient posts in message boards
	
	class META:
		admin = meta.Admin(
			search_fields = (
				'userName', 'realName', 'email'
			),
			list_display = (
				'userName', 'realName', 'email', 'dateJoined'
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
		ordering = ('userName',)
	
	def __repr__(self):
		return self.userName
		
	def _module_checkPassword(plaintextPass, encryptedPass):
		import crypt
		"""Checks a password is valid"""
		return crypt.crypt(plaintextPass, encryptedPass) == encryptedPass
	
	def _module_generateSalt():
		import random, datetime
		rand64= "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
		random.seed(datetime.datetime.today().microsecond)
		return rand64[int(random.random()*64)] + rand64[int(random.random()*64)]
	
	def _module_encryptPassword(userPass):
		import crypt
		"""Encrypt a users password"""
		# written to maintain compatibility with existing password file
		return crypt.crypt(userPass, generateSalt())

class Award(meta.Model):
	name = meta.CharField("Award name", maxlength=50)
	image = meta.ImageField("Award image", 
		upload_to = AWARD_UPLOAD_PATH)

	def __repr__(self):
		return self.name
	
	class META:
		admin = meta.Admin()
		ordering = ('name',)
		
	
class PersonalAward(meta.Model):
	reason = meta.CharField("Reason for award", maxlength=200)
	dateAwarded = meta.DateField("Date awarded", null=True, blank=True)
	award = meta.ForeignKey(Award,
		verbose_name="award", 
		related_name="personalAward")
	user = meta.ForeignKey(User,
		verbose_name="user",
		related_name="personalAward")
		
	def __repr__(self):
		return self.get_award().name + " to " + self.get_user().userName
		
		
	class META:
		admin = meta.Admin(
			list_display = ('award', 'user','reason', 'dateAwarded')
		)
		ordering = ('dateAwarded',)

BOOKMARK_CATEGORIES = (
	(0, "Often visited"),
	(1, "Classics")
)

class Bookmark(meta.Model):
	url = meta.CharField("URL", maxlength="60") # 60?
	title = meta.CharField("Title", maxlength="50") # 100?
	user = meta.ForeignKey(User, verbose_name="user",
		related_name="bookmark")
	lastUpdated = meta.DateTimeField("Last updated",
		null=True, blank=True)
	lastSeen = meta.DateTimeField("Last seen",
		null=True, blank=True)
	category = meta.PositiveSmallIntegerField("Category", choices = BOOKMARK_CATEGORIES)
	
	class META:
		admin = meta.Admin()
		ordering = ('category', '-lastUpdated')
	
	def __repr__(self):
		return self.title

MESSAGE_BOXES = (
	(0, "Inbox"),
	(1, "Saved")
)

class Message(meta.Model):
	fromUser = meta.ForeignKey(User,
		verbose_name="from user",
		related_name="messageSent"
	)
	toUser = meta.ForeignKey(User, 
		verbose_name="to user",
		related_name="messageReceived")
	time = meta.DateTimeField("At")
	text = meta.TextField("Message")
	box = meta.PositiveSmallIntegerField("Message box",
		choices = MESSAGE_BOXES)
	
	def __repr__(self):
		#return str(self.id)
		return "[" + str(self.id) + "] to " + repr(self.get_toUser())  + " from " + repr(self.get_fromUser())
	
	class META:
		admin = meta.Admin(
			list_display = ('toUser', 'fromUser', 'time')
		)
		ordering = ('-time',)

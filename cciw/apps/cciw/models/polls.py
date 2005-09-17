from django.core import meta
from members import *

VOTING_RULES = (
	(0, "Unlimited"),
	(1, "'X' votes per member"),
	(2, "'X' votes per member per day")
)

class Poll(meta.Model):
	title = meta.CharField("Title", maxlength=100)
	introText = meta.CharField("Intro text", maxlength=200)
	outroText = meta.CharField("Closing text", maxlength=200)
	open = meta.BooleanField("Open", default=True)
	votingStarts = meta.DateTimeField("Voting starts")
	votingEnds = meta.DateTimeField("Voting ends")
	rules = meta.PositiveSmallIntegerField("Rules",
		choices = VOTING_RULES)
	ruleParameter = meta.PositiveSmallIntegerField("Parameter for rule", default=1)
	haveVoteInfo = meta.BooleanField("Full vote information available", default=True)
	createdBy = meta.ForeignKey(Member, verbose_name="created by",
		related_name="pollCreated")
	
	def __repr__(self):
		return self.title
	
	class META:
		admin = meta.Admin(
			list_display = ('title', 'createdBy', 'votingStarts')
		)
		module_constants = {
			'UNLIMITED': 0,
			'X_VOTES_PER_USER': 1,
			'X_VOTES_PER_USER_PER_DAY': 2
		}
		ordering = ('title',)
		
		

class PollOption(meta.Model):
	text = meta.CharField("Option text", maxlength=200)
	total = meta.PositiveSmallIntegerField("Number of votes")
	poll = meta.ForeignKey(Poll, verbose_name="Associated poll",
		related_name="pollOption")
	listorder = meta.PositiveSmallIntegerField("Order in list")
		
	def __repr__(self):
		return self.text
		
	class META:
		admin = meta.Admin(
			list_display = ('text', 'poll')
		)
		ordering = ('poll', 'listorder',)
	

class VoteInfo(meta.Model):
	pollOption = meta.ForeignKey(PollOption, 
		verbose_name="pollOption",
		related_name="vote")
	member = meta.ForeignKey(Member,
		verbose_name="member",
		related_name="pollVote")
	date = meta.DateTimeField("Date")

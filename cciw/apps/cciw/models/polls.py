from django.db import models
from members import *

VOTING_RULES = (
    (0, "Unlimited"),
    (1, "'X' votes per member"),
    (2, "'X' votes per member per day")
)

class Poll(models.Model):
    UNLIMITED = 0
    X_VOTES_PER_USER = 1
    X_VOTES_PER_USER_PER_DAY = 2

    title = models.CharField("Title", maxlength=100)
    intro_text = models.CharField("Intro text", maxlength=200)
    outro_text = models.CharField("Closing text", maxlength=200)
    open = models.BooleanField("Open", default=True)
    voting_starts = models.DateTimeField("Voting starts")
    voting_ends = models.DateTimeField("Voting ends")
    rules = models.PositiveSmallIntegerField("Rules",
        choices = VOTING_RULES)
    rule_parameter = models.PositiveSmallIntegerField("Parameter for rule", 
        default=1)
    have_vote_info = models.BooleanField("Full vote information available", 
        default=True)
    created_by = models.ForeignKey(Member, verbose_name="created by",
        related_name="poll_created")
    
    def __repr__(self):
        return self.title
    
    def can_vote(self, member):
        """Returns true if member can vote on the poll"""
        # TODO
        return True
        
    def total_votes(self):
        sum = 0
        # TODO - use SQL
        for option in self.poll_options.all():
            sum += option.total
        return sum
        
    class Meta:
        app_label = "cciw"   
        ordering = ('title',)
        
    class Admin:
        list_display = ('title', 'created_by', 'voting_starts')
        

class PollOption(models.Model):
    text = models.CharField("Option text", maxlength=200)
    total = models.PositiveSmallIntegerField("Number of votes")
    poll = models.ForeignKey(Poll, verbose_name="Associated poll",
        related_name="poll_options")
    listorder = models.PositiveSmallIntegerField("Order in list")
        
    def __repr__(self):
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
            return int(float(self.total)/sum*400)
            
        
    class Meta:
        app_label = "cciw"
        ordering = ('poll', 'listorder',)

    class Admin:
        list_display = ('text', 'poll')

class VoteInfo(models.Model):
    poll_option = models.ForeignKey(PollOption, 
        verbose_name="poll_option",
        related_name="vote")
    member = models.ForeignKey(Member,
        verbose_name="member",
        related_name="poll_vote")
    date = models.DateTimeField("Date")

    class Meta:
        app_label = "cciw"
        

from django.db import models
from datetime import datetime, timedelta
from cciw.cciwmain.models.members import Member
import operator

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

    def __unicode__(self):
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
                queries.append(po.votes.filter(member=member.user_name))
            elif self.rules == Poll.X_VOTES_PER_USER_PER_DAY:
                queries.append(po.votes.filter(member=member.user_name,
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
        sum = 0
        # TODO - use SQL, or caching
        for option in self.poll_options.all():
            sum += option.total
        return sum

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
        app_label = "cciwmain"
        ordering = ('title',)

class PollOption(models.Model):
    text = models.CharField("Option text", max_length=200, core=True)
    total = models.PositiveSmallIntegerField("Number of votes", core=True)
    poll = models.ForeignKey(Poll, verbose_name="Associated poll",
        related_name="poll_options", edit_inline=True)
    listorder = models.PositiveSmallIntegerField("Order in list", core=True)

    def __unicode__(self):
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
        app_label = "cciwmain"
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

    class Meta:
        app_label = "cciwmain"


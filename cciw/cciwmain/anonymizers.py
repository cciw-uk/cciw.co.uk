from cciw.cciwmain.models import Member, PersonalAward, Message, Poll, PollOption, NewsItem, Topic, Photo, Post
from anonymizer import Anonymizer

class MemberAnonymizer(Anonymizer):

    model = Member

    attributes = [
         # Skipping field id
        ('user_name', "username"),
        ('real_name', "name"),
        ('email', "email"),
        ('password', "varchar"),
        ('date_joined', "similar_datetime"),
        ('last_seen', "similar_datetime"),
        ('comments', "similar_lorem"),
    ]

    def get_query_set(self):
        # Don't alter developer logins.
        return super(MemberAnonymizer, self).get_query_set().exclude(user_name='spookylukey')


class PersonalAwardAnonymizer(Anonymizer):

    model = PersonalAward

    attributes = [
        ('reason', "similar_lorem"),
    ]


class MessageAnonymizer(Anonymizer):

    model = Message

    attributes = [
        ('text', "similar_lorem"),
    ]

class PollAnonymizer(Anonymizer):

    model = Poll

    attributes = [
        ('title', "similar_lorem"),
        ('intro_text', "similar_lorem"),
        ('outro_text', "similar_lorem"),
    ]


class PollOptionAnonymizer(Anonymizer):

    model = PollOption

    attributes = [
        ('text', "similar_lorem"),
    ]


class NewsItemAnonymizer(Anonymizer):

    model = NewsItem

    attributes = [
        ('summary', "similar_lorem"),
        ('full_item', "similar_lorem"),
        ('subject', "similar_lorem"),
    ]


class TopicAnonymizer(Anonymizer):

    model = Topic

    attributes = [
        ('subject', "similar_lorem"),
    ]


class PhotoAnonymizer(Anonymizer):

    model = Photo

    attributes = [
        ('description', "similar_lorem"),
    ]


class PostAnonymizer(Anonymizer):

    model = Post

    attributes = [
        ('subject', "similar_lorem"),
        ('message', "similar_lorem"),
    ]
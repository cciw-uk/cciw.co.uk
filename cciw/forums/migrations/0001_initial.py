# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Award',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('name', models.CharField(max_length=50, verbose_name='Award name')),
                ('value', models.SmallIntegerField(verbose_name='Value')),
                ('year', models.PositiveSmallIntegerField(verbose_name='Year')),
                ('description', models.CharField(max_length=200, verbose_name='Description')),
                ('image', models.ImageField(upload_to='images/awards', verbose_name='Award image')),
            ],
            options={
                'ordering': ('-year', 'name'),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Forum',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('open', models.BooleanField(default=True, verbose_name='Open')),
                ('location', models.CharField(unique=True, db_index=True, max_length=50, verbose_name='Location/path')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Gallery',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('location', models.CharField(max_length=50, verbose_name='Location/URL')),
                ('needs_approval', models.BooleanField(default=False, verbose_name='Photos need approval')),
            ],
            options={
                'verbose_name_plural': 'Galleries',
                'ordering': ('-location',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Member',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('user_name', models.CharField(unique=True, max_length=30, verbose_name='User name')),
                ('real_name', models.CharField(blank=True, max_length=30, verbose_name="'Real' name")),
                ('email', models.EmailField(max_length=75, verbose_name='Email address')),
                ('password', models.CharField(max_length=255, verbose_name='Password')),
                ('date_joined', models.DateTimeField(null=True, verbose_name='Date joined')),
                ('last_seen', models.DateTimeField(null=True, verbose_name='Last on website')),
                ('show_email', models.BooleanField(default=False, verbose_name='Make email address visible')),
                ('message_option', models.PositiveSmallIntegerField(default=1, choices=[(0, "Don't allow messages"), (1, 'Store messages on the website'), (2, 'Send messages via email'), (3, 'Store messages and send via email')], verbose_name='Message storing')),
                ('comments', models.TextField(blank=True, verbose_name='Comments')),
                ('moderated', models.PositiveSmallIntegerField(default=0, choices=[(0, 'Off'), (1, 'Unmoderated, but notify'), (2, 'Fully moderated')], verbose_name='Moderated')),
                ('hidden', models.BooleanField(default=False, verbose_name='Hidden')),
                ('banned', models.BooleanField(default=False, verbose_name='Banned')),
                ('icon', models.ImageField(blank=True, upload_to='images/members/temp', verbose_name='Icon')),
                ('dummy_member', models.BooleanField(default=False, verbose_name='Dummy member status')),
            ],
            options={
                'ordering': ('user_name',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('time', models.DateTimeField(verbose_name='At')),
                ('text', models.TextField(verbose_name='Message')),
                ('box', models.PositiveSmallIntegerField(choices=[(0, 'Inbox'), (1, 'Saved')], verbose_name='Message box')),
                ('from_member', models.ForeignKey(related_name='messages_sent', to='forums.Member', verbose_name='from member')),
                ('to_member', models.ForeignKey(related_name='messages_received', to='forums.Member', verbose_name='to member')),
            ],
            options={
                'ordering': ('-time',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='NewsItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('created_at', models.DateTimeField(verbose_name='Posted')),
                ('summary', models.TextField(verbose_name='Summary or short item, (bbcode)')),
                ('full_item', models.TextField(blank=True, verbose_name='Full post (HTML)')),
                ('subject', models.CharField(max_length=100, verbose_name='Subject')),
                ('created_by', models.ForeignKey(to='forums.Member', related_name='news_items_created')),
            ],
            options={
                'ordering': ('-created_at',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Permission',
            fields=[
                ('id', models.PositiveSmallIntegerField(primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(max_length=40, verbose_name='Description')),
            ],
            options={
                'ordering': ('id',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PersonalAward',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('reason', models.CharField(max_length=200, verbose_name='Reason for award')),
                ('date_awarded', models.DateField(blank=True, null=True, verbose_name='Date awarded')),
                ('award', models.ForeignKey(related_name='personal_awards', to='forums.Award', verbose_name='award')),
                ('member', models.ForeignKey(related_name='personal_awards', to='forums.Member', verbose_name='member')),
            ],
            options={
                'ordering': ('date_awarded',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Photo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('created_at', models.DateTimeField(null=True, verbose_name='Started')),
                ('open', models.BooleanField(default=False, verbose_name='Open')),
                ('hidden', models.BooleanField(default=False, verbose_name='Hidden')),
                ('filename', models.CharField(max_length=50, verbose_name='Filename')),
                ('description', models.CharField(blank=True, max_length=100, verbose_name='Description')),
                ('approved', models.NullBooleanField(verbose_name='Approved')),
                ('needs_approval', models.BooleanField(default=False, verbose_name='Needs approval')),
                ('last_post_at', models.DateTimeField(blank=True, null=True, verbose_name='Last post at')),
                ('post_count', models.PositiveSmallIntegerField(default=0, verbose_name='Number of posts')),
                ('checked_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True, blank=True, related_name='photos_checked')),
                ('gallery', models.ForeignKey(related_name='photos', to='forums.Gallery', verbose_name='gallery')),
                ('last_post_by', models.ForeignKey(to='forums.Member', null=True, blank=True, related_name='photos_with_last_post', verbose_name='Last post by')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Poll',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('title', models.CharField(max_length=100, verbose_name='Title')),
                ('intro_text', models.CharField(blank=True, max_length=400, verbose_name='Intro text')),
                ('outro_text', models.CharField(blank=True, max_length=400, verbose_name='Closing text')),
                ('voting_starts', models.DateTimeField(verbose_name='Voting starts')),
                ('voting_ends', models.DateTimeField(verbose_name='Voting ends')),
                ('rules', models.PositiveSmallIntegerField(choices=[(0, 'Unlimited'), (1, "'X' votes per member"), (2, "'X' votes per member per day")], verbose_name='Rules')),
                ('rule_parameter', models.PositiveSmallIntegerField(default=1, verbose_name='Parameter for rule')),
                ('have_vote_info', models.BooleanField(default=True, verbose_name='Full vote information available')),
                ('created_by', models.ForeignKey(related_name='polls_created', to='forums.Member', verbose_name='created by')),
            ],
            options={
                'ordering': ('title',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PollOption',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('text', models.CharField(max_length=200, verbose_name='Option text')),
                ('total', models.PositiveSmallIntegerField(verbose_name='Number of votes')),
                ('listorder', models.PositiveSmallIntegerField(verbose_name='Order in list')),
                ('poll', models.ForeignKey(related_name='poll_options', to='forums.Poll', verbose_name='Associated poll')),
            ],
            options={
                'ordering': ('poll', 'listorder'),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('subject', models.CharField(blank=True, max_length=240, verbose_name='Subject')),
                ('message', models.TextField(verbose_name='Message')),
                ('posted_at', models.DateTimeField(null=True, verbose_name='Posted at')),
                ('hidden', models.BooleanField(default=False, verbose_name='Hidden')),
                ('approved', models.NullBooleanField(verbose_name='Approved')),
                ('needs_approval', models.BooleanField(default=False, verbose_name='Needs approval')),
                ('checked_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True, blank=True, related_name='checked_post', verbose_name='checked by')),
                ('photo', models.ForeignKey(to='forums.Photo', null=True, blank=True, related_name='posts')),
                ('posted_by', models.ForeignKey(to='forums.Member', related_name='posts')),
            ],
            options={
                'ordering': ('id',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Topic',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('subject', models.CharField(max_length=240, verbose_name='Subject')),
                ('created_at', models.DateTimeField(null=True, verbose_name='Started')),
                ('open', models.BooleanField(default=False, verbose_name='Open')),
                ('hidden', models.BooleanField(default=False, verbose_name='Hidden')),
                ('approved', models.NullBooleanField(verbose_name='Approved')),
                ('needs_approval', models.BooleanField(default=False, verbose_name='Needs approval')),
                ('last_post_at', models.DateTimeField(blank=True, null=True, verbose_name='Last post at')),
                ('post_count', models.PositiveSmallIntegerField(default=0, verbose_name='Number of posts')),
                ('checked_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True, blank=True, related_name='topics_checked', verbose_name='checked by')),
                ('forum', models.ForeignKey(to='forums.Forum', related_name='topics')),
                ('last_post_by', models.ForeignKey(to='forums.Member', null=True, blank=True, related_name='topics_with_last_post', verbose_name='Last post by')),
                ('news_item', models.ForeignKey(to='forums.NewsItem', null=True, blank=True, related_name='topics')),
                ('poll', models.ForeignKey(to='forums.Poll', null=True, blank=True, related_name='topics')),
                ('started_by', models.ForeignKey(related_name='topics_started', to='forums.Member', verbose_name='started by')),
            ],
            options={
                'ordering': ('-started_by',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='VoteInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('date', models.DateTimeField(verbose_name='Date')),
                ('member', models.ForeignKey(related_name='poll_votes', to='forums.Member', verbose_name='member')),
                ('poll_option', models.ForeignKey(to='forums.PollOption', related_name='votes')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='post',
            name='topic',
            field=models.ForeignKey(to='forums.Topic', null=True, blank=True, related_name='posts'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='member',
            name='permissions',
            field=models.ManyToManyField(to='forums.Permission', blank=True, related_name='member_with_permission', verbose_name='permissions'),
            preserve_default=True,
        ),
    ]

# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Member.password'
        db.alter_column('forums_member', 'password', self.gf('django.db.models.fields.CharField')(max_length=255))

    def backwards(self, orm):

        # Changing field 'Member.password'
        db.alter_column('forums_member', 'password', self.gf('django.db.models.fields.CharField')(max_length=30))

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission', 'ordering': "('content_type__app_label', 'content_type__model', 'codename')"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'blank': 'True', 'max_length': '75'}),
            'first_name': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '30'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'user_set'", 'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '30'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'user_set'", 'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'", 'ordering': "('name',)"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'forums.award': {
            'Meta': {'object_name': 'Award', 'ordering': "('-year', 'name')"},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'value': ('django.db.models.fields.SmallIntegerField', [], {}),
            'year': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'forums.forum': {
            'Meta': {'object_name': 'Forum'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'unique': 'True', 'db_index': 'True', 'max_length': '50'}),
            'open': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'forums.gallery': {
            'Meta': {'object_name': 'Gallery', 'ordering': "('-location',)"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'needs_approval': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'forums.member': {
            'Meta': {'object_name': 'Member', 'ordering': "('user_name',)"},
            'banned': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'comments': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'dummy_member': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'icon': ('django.db.models.fields.files.ImageField', [], {'blank': 'True', 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_seen': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'message_option': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1'}),
            'moderated': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'member_with_permission'", 'null': 'True', 'to': "orm['forums.Permission']", 'blank': 'True'}),
            'real_name': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '30'}),
            'show_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user_name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'forums.message': {
            'Meta': {'object_name': 'Message', 'ordering': "('-time',)"},
            'box': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'from_member': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages_sent'", 'to': "orm['forums.Member']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'time': ('django.db.models.fields.DateTimeField', [], {}),
            'to_member': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages_received'", 'to': "orm['forums.Member']"})
        },
        'forums.newsitem': {
            'Meta': {'object_name': 'NewsItem', 'ordering': "('-created_at',)"},
            'created_at': ('django.db.models.fields.DateTimeField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'news_items_created'", 'to': "orm['forums.Member']"}),
            'full_item': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'summary': ('django.db.models.fields.TextField', [], {})
        },
        'forums.permission': {
            'Meta': {'object_name': 'Permission', 'ordering': "('id',)"},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'id': ('django.db.models.fields.PositiveSmallIntegerField', [], {'primary_key': 'True'})
        },
        'forums.personalaward': {
            'Meta': {'object_name': 'PersonalAward', 'ordering': "('date_awarded',)"},
            'award': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'personal_awards'", 'to': "orm['forums.Award']"}),
            'date_awarded': ('django.db.models.fields.DateField', [], {'blank': 'True', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'member': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'personal_awards'", 'to': "orm['forums.Member']"}),
            'reason': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'forums.photo': {
            'Meta': {'object_name': 'Photo'},
            'approved': ('django.db.models.fields.NullBooleanField', [], {'blank': 'True', 'null': 'True'}),
            'checked_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'photos_checked'", 'null': 'True', 'to': "orm['auth.User']", 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '100'}),
            'filename': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'gallery': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'photos'", 'to': "orm['forums.Gallery']"}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post_at': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'null': 'True'}),
            'last_post_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'photos_with_last_post'", 'null': 'True', 'to': "orm['forums.Member']", 'blank': 'True'}),
            'needs_approval': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'open': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'post_count': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'})
        },
        'forums.poll': {
            'Meta': {'object_name': 'Poll', 'ordering': "('title',)"},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polls_created'", 'to': "orm['forums.Member']"}),
            'have_vote_info': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'intro_text': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '400'}),
            'outro_text': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '400'}),
            'rule_parameter': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1'}),
            'rules': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'voting_ends': ('django.db.models.fields.DateTimeField', [], {}),
            'voting_starts': ('django.db.models.fields.DateTimeField', [], {})
        },
        'forums.polloption': {
            'Meta': {'object_name': 'PollOption', 'ordering': "('poll', 'listorder')"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'listorder': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'poll': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'poll_options'", 'to': "orm['forums.Poll']"}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'total': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'forums.post': {
            'Meta': {'object_name': 'Post', 'ordering': "('id',)"},
            'approved': ('django.db.models.fields.NullBooleanField', [], {'blank': 'True', 'null': 'True'}),
            'checked_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'checked_post'", 'null': 'True', 'to': "orm['auth.User']", 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'needs_approval': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'photo': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'null': 'True', 'to': "orm['forums.Photo']", 'blank': 'True'}),
            'posted_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'to': "orm['forums.Member']"}),
            'subject': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '240'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'null': 'True', 'to': "orm['forums.Topic']", 'blank': 'True'})
        },
        'forums.topic': {
            'Meta': {'object_name': 'Topic', 'ordering': "('-started_by',)"},
            'approved': ('django.db.models.fields.NullBooleanField', [], {'blank': 'True', 'null': 'True'}),
            'checked_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topics_checked'", 'null': 'True', 'to': "orm['auth.User']", 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'forum': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topics'", 'to': "orm['forums.Forum']"}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post_at': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'null': 'True'}),
            'last_post_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topics_with_last_post'", 'null': 'True', 'to': "orm['forums.Member']", 'blank': 'True'}),
            'needs_approval': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'news_item': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topics'", 'null': 'True', 'to': "orm['forums.NewsItem']", 'blank': 'True'}),
            'open': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'poll': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topics'", 'null': 'True', 'to': "orm['forums.Poll']", 'blank': 'True'}),
            'post_count': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'started_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topics_started'", 'to': "orm['forums.Member']"}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '240'})
        },
        'forums.voteinfo': {
            'Meta': {'object_name': 'VoteInfo'},
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'member': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'poll_votes'", 'to': "orm['forums.Member']"}),
            'poll_option': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'votes'", 'to': "orm['forums.PollOption']"})
        }
    }

    complete_apps = ['forums']
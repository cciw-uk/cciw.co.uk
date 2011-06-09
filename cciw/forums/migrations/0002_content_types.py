# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    tables = ['photo','poll','topic','award','post','polloption','forum',
              'personalaward','message','voteinfo','member','member_permissions',
              'gallery','newsitem','permission']

    def forwards(self, orm):
        for table in self.tables:
            orm['contenttypes.ContentType'].objects.filter(app_label='cciwmain',
                                                           model=table).update(app_label='forums')

    def backwards(self, orm):
        for table in self.tables:
            orm['contenttypes.ContentType'].objects.filter(app_label='forums',
                                                           model=table).update(app_label='cciwmain')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80', 'unique': 'True'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '30', 'unique': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'forums.award': {
            'Meta': {'ordering': "('-year', 'name')", 'object_name': 'Award'},
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
            'location': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'db_index': 'True'}),
            'open': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'forums.gallery': {
            'Meta': {'ordering': "('-location',)", 'object_name': 'Gallery'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'needs_approval': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'forums.member': {
            'Meta': {'ordering': "('user_name',)", 'object_name': 'Member'},
            'banned': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'comments': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'dummy_member': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'icon': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_seen': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'message_option': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1'}),
            'moderated': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'member_with_permission'", 'blank': 'True', 'null': 'True', 'to': "orm['forums.Permission']"}),
            'real_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'show_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'unique': 'True'})
        },
        'forums.message': {
            'Meta': {'ordering': "('-time',)", 'object_name': 'Message'},
            'box': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'from_member': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages_sent'", 'to': "orm['forums.Member']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'time': ('django.db.models.fields.DateTimeField', [], {}),
            'to_member': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages_received'", 'to': "orm['forums.Member']"})
        },
        'forums.newsitem': {
            'Meta': {'ordering': "('-created_at',)", 'object_name': 'NewsItem'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'news_items_created'", 'to': "orm['forums.Member']"}),
            'full_item': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'summary': ('django.db.models.fields.TextField', [], {})
        },
        'forums.permission': {
            'Meta': {'ordering': "('id',)", 'object_name': 'Permission'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'id': ('django.db.models.fields.PositiveSmallIntegerField', [], {'primary_key': 'True'})
        },
        'forums.personalaward': {
            'Meta': {'ordering': "('date_awarded',)", 'object_name': 'PersonalAward'},
            'award': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'personal_awards'", 'to': "orm['forums.Award']"}),
            'date_awarded': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'member': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'personal_awards'", 'to': "orm['forums.Member']"}),
            'reason': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'forums.photo': {
            'Meta': {'object_name': 'Photo'},
            'approved': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'checked_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'photos_checked'", 'blank': 'True', 'null': 'True', 'to': "orm['auth.User']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'gallery': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'photos'", 'to': "orm['forums.Gallery']"}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_post_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'photos_with_last_post'", 'blank': 'True', 'null': 'True', 'to': "orm['forums.Member']"}),
            'needs_approval': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'open': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'post_count': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'})
        },
        'forums.poll': {
            'Meta': {'ordering': "('title',)", 'object_name': 'Poll'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polls_created'", 'to': "orm['forums.Member']"}),
            'have_vote_info': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'intro_text': ('django.db.models.fields.CharField', [], {'max_length': '400', 'blank': 'True'}),
            'outro_text': ('django.db.models.fields.CharField', [], {'max_length': '400', 'blank': 'True'}),
            'rule_parameter': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1'}),
            'rules': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'voting_ends': ('django.db.models.fields.DateTimeField', [], {}),
            'voting_starts': ('django.db.models.fields.DateTimeField', [], {})
        },
        'forums.polloption': {
            'Meta': {'ordering': "('poll', 'listorder')", 'object_name': 'PollOption'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'listorder': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'poll': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'poll_options'", 'to': "orm['forums.Poll']"}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'total': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'forums.post': {
            'Meta': {'ordering': "('id',)", 'object_name': 'Post'},
            'approved': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'checked_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'checked_post'", 'blank': 'True', 'null': 'True', 'to': "orm['auth.User']"}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'needs_approval': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'photo': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'blank': 'True', 'null': 'True', 'to': "orm['forums.Photo']"}),
            'posted_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'to': "orm['forums.Member']"}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '240', 'blank': 'True'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'blank': 'True', 'null': 'True', 'to': "orm['forums.Topic']"})
        },
        'forums.topic': {
            'Meta': {'ordering': "('-started_by',)", 'object_name': 'Topic'},
            'approved': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'checked_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topics_checked'", 'blank': 'True', 'null': 'True', 'to': "orm['auth.User']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'forum': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topics'", 'to': "orm['forums.Forum']"}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_post_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topics_with_last_post'", 'blank': 'True', 'null': 'True', 'to': "orm['forums.Member']"}),
            'needs_approval': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'news_item': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topics'", 'blank': 'True', 'null': 'True', 'to': "orm['forums.NewsItem']"}),
            'open': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'poll': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topics'", 'blank': 'True', 'null': 'True', 'to': "orm['forums.Poll']"}),
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

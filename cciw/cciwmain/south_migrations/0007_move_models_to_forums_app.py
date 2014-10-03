# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        pass
    def backwards(self, orm):
        pass

    depends_on = [
        ('forums', '0001_initial'),
        ]

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
        'cciwmain.camp': {
            'Meta': {'ordering': "['-year', 'number']", 'unique_together': "(('year', 'number'),)", 'object_name': 'Camp'},
            'admins': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'camps_as_admin'", 'blank': 'True', 'null': 'True', 'to': "orm['auth.User']"}),
            'age': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'chaplain': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'camps_as_chaplain'", 'blank': 'True', 'null': 'True', 'to': "orm['cciwmain.Person']"}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'leaders': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'camps_as_leader'", 'blank': 'True', 'null': 'True', 'to': "orm['cciwmain.Person']"}),
            'number': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'officers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'through': "orm['officers.Invitation']", 'symmetrical': 'False'}),
            'online_applications': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'previous_camp': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'next_camps'", 'blank': 'True', 'null': 'True', 'to': "orm['cciwmain.Camp']"}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cciwmain.Site']"}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'year': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'cciwmain.htmlchunk': {
            'Meta': {'object_name': 'HtmlChunk'},
            'html': ('django.db.models.fields.TextField', [], {}),
            'menu_link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cciwmain.MenuLink']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True', 'db_index': 'True'}),
            'page_title': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'})
        },
        'cciwmain.menulink': {
            'Meta': {'ordering': "('-parent_item__id', 'listorder')", 'object_name': 'MenuLink'},
            'extra_title': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'listorder': ('django.db.models.fields.SmallIntegerField', [], {}),
            'parent_item': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'child_links'", 'blank': 'True', 'null': 'True', 'to': "orm['cciwmain.MenuLink']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'visible': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'cciwmain.person': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Person'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'cciwmain.site': {
            'Meta': {'object_name': 'Site'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('django.db.models.fields.TextField', [], {}),
            'long_name': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': "'25'", 'unique': 'True'}),
            'slug_name': ('django.db.models.fields.SlugField', [], {'db_index': 'True', 'max_length': "'25'", 'unique': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'officers.invitation': {
            'Meta': {'ordering': "('-camp__year', 'officer__first_name', 'officer__last_name')", 'unique_together': "(('officer', 'camp'),)", 'object_name': 'Invitation'},
            'camp': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cciwmain.Camp']"}),
            'date_added': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'notes': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'officer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['cciwmain']

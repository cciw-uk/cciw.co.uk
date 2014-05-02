# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Site.long_name'
        db.alter_column('cciwmain_site', 'long_name', self.gf('django.db.models.fields.CharField')(max_length=50))

        # Changing field 'Site.short_name'
        db.alter_column('cciwmain_site', 'short_name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=25))

        # Changing field 'Site.slug_name'
        db.alter_column('cciwmain_site', 'slug_name', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=25))

    def backwards(self, orm):

        # Changing field 'Site.long_name'
        db.alter_column('cciwmain_site', 'long_name', self.gf('django.db.models.fields.CharField')(max_length='50'))

        # Changing field 'Site.short_name'
        db.alter_column('cciwmain_site', 'short_name', self.gf('django.db.models.fields.CharField')(unique=True, max_length='25'))

        # Changing field 'Site.slug_name'
        db.alter_column('cciwmain_site', 'slug_name', self.gf('django.db.models.fields.SlugField')(unique=True, max_length='25'))

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'blank': 'True', 'to': "orm['auth.Permission']"})
        },
        'auth.permission': {
            'Meta': {'object_name': 'Permission', 'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)"},
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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'blank': 'True', 'related_name': "'user_set'", 'to': "orm['auth.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'blank': 'True', 'related_name': "'user_set'", 'to': "orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cciwmain.camp': {
            'Meta': {'object_name': 'Camp', 'ordering': "['-year', 'number']", 'unique_together': "(('year', 'number'),)"},
            'admins': ('django.db.models.fields.related.ManyToManyField', [], {'null': 'True', 'symmetrical': 'False', 'blank': 'True', 'related_name': "'camps_as_admin'", 'to': "orm['auth.User']"}),
            'chaplain': ('django.db.models.fields.related.ForeignKey', [], {'null': 'True', 'to': "orm['cciwmain.Person']", 'blank': 'True', 'related_name': "'camps_as_chaplain'"}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'leaders': ('django.db.models.fields.related.ManyToManyField', [], {'null': 'True', 'symmetrical': 'False', 'blank': 'True', 'related_name': "'camps_as_leader'", 'to': "orm['cciwmain.Person']"}),
            'max_campers': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '80'}),
            'max_female_campers': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '60'}),
            'max_male_campers': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '60'}),
            'maximum_age': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'minimum_age': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'number': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'officers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'through': "orm['officers.Invitation']", 'to': "orm['auth.User']"}),
            'online_applications': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'previous_camp': ('django.db.models.fields.related.ForeignKey', [], {'null': 'True', 'to': "orm['cciwmain.Camp']", 'blank': 'True', 'related_name': "'next_camps'"}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cciwmain.Site']"}),
            'south_wales_transport_available': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'year': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'cciwmain.person': {
            'Meta': {'object_name': 'Person', 'ordering': "('name',)"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'blank': 'True', 'to': "orm['auth.User']"})
        },
        'cciwmain.site': {
            'Meta': {'object_name': 'Site'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('django.db.models.fields.TextField', [], {}),
            'long_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'short_name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '25'}),
            'slug_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'blank': 'True', 'max_length': '25'})
        },
        'contenttypes.contenttype': {
            'Meta': {'object_name': 'ContentType', 'db_table': "'django_content_type'", 'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'officers.invitation': {
            'Meta': {'object_name': 'Invitation', 'ordering': "('-camp__year', 'officer__first_name', 'officer__last_name')", 'unique_together': "(('officer', 'camp'),)"},
            'camp': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cciwmain.Camp']"}),
            'date_added': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'notes': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'officer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['cciwmain']
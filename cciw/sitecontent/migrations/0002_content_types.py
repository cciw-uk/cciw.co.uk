# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    tables = ['htmlchunk', 'menulink']

    def forwards(self, orm):
        for table in self.tables:
            orm['contenttypes.ContentType'].objects.filter(app_label='cciwmain',
                                                           model=table).update(app_label='sitecontent')

    def backwards(self, orm):
        for table in self.tables:
            orm['contenttypes.ContentType'].objects.filter(app_label='sitecontent',
                                                           model=table).update(app_label='cciwmain')


    models = {
        'sitecontent.htmlchunk': {
            'Meta': {'object_name': 'HtmlChunk'},
            'html': ('django.db.models.fields.TextField', [], {}),
            'menu_link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sitecontent.MenuLink']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True', 'db_index': 'True'}),
            'page_title': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'})
        },
        'sitecontent.menulink': {
            'Meta': {'ordering': "('-parent_item__id', 'listorder')", 'object_name': 'MenuLink'},
            'extra_title': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'listorder': ('django.db.models.fields.SmallIntegerField', [], {}),
            'parent_item': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'child_links'", 'blank': 'True', 'null': 'True', 'to': "orm['sitecontent.MenuLink']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'visible': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
    }

    complete_apps = ['sitecontent']

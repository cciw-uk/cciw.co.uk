# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        h1, x = orm['sitecontent.HtmlChunk'].objects.get_or_create(name="camp_dates_outro_text")
        h1.html = """
<br/><br/><h2>See also:</h2>
<ul>
    <li><a href="/info/about-camp/">What is camp all about?</a></li>
    <li><a href="/booking/">Booking and prices</a></li>
    <li><a href="/thisyear/transport/">Transport to camp</a></li>
    <li><a href="/info/legal/">Insurance</a></li>
</ul>
"""
        h1.save()


        orm['sitecontent.HtmlChunk'].objects.filter(name='booking_overview').delete()
        orm['sitecontent.HtmlChunk'].objects.filter(name='bookingform_start').delete()
        orm['sitecontent.HtmlChunk'].objects.filter(name='bookingform_end').delete()


        orm['sitecontent.MenuLink'].objects.filter(title='About').update(visible=False)

        if orm['sitecontent.MenuLink'].objects.filter(url='/booking/'):
            m1 = orm['sitecontent.MenuLink'].objects.get(url='/booking/')
        else:
            m1 = orm['sitecontent.MenuLink'](url='/booking/')
        m1.visible = True
        m1.listorder = 350
        m1.title = u"Booking"
        m1.save()


    def backwards(self, orm):
        "Write your backwards methods here."


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
            'parent_item': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'child_links'", 'null': 'True', 'to': "orm['sitecontent.MenuLink']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'visible': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        }
    }

    complete_apps = ['sitecontent']

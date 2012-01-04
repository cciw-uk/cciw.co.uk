# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        h1, x = orm['sitecontent.HtmlChunk'].objects.get_or_create(name="booking_overview")
        h1.html = """
<h2>Booking</h2>

<p>There are two ways to book for camp:</p>

<h3>Paper booking</h3>

<p>You will need the booking form which comes with our camp brochure, which we can post to you, or you can download below. You will need to include a cheque to pay a deposit of £20 with your booking</p>

<h3>Online booking</h3>

<p>You can <a href="/booking/start/">book and pay online</a>, providing you have a debit card, credit card, or PayPal account.</p>

<p>If you book online, you can see how many places there are left in real time, and your place will be confirmed immediately. However, you will have to pay the full amount when booking, not just the deposit. For refunds, the same rules apply to both paper bookings and online bookings.<p>
"""
        h1.save()

        h2, x = orm['sitecontent.HtmlChunk'].objects.get_or_create(name="bookingform_start")
        h2.html = """
<h2>Paper booking form</h2>

<p>If you have a printer you can download and print a booking form for {{thisyear}}.  Please fill in the form and follow the instructions on it.  You will need a PDF reader to view or print the form.</p>
"""
        h2.save()

        h3, x = orm['sitecontent.HtmlChunk'].objects.get_or_create(name="bookingform_end")
        h3.html = """
<p><br/>The completed booking form must be sent to:</p>

<p>Alan Lansdown<br/>
28 Bryntirion<br/>
Rhiwbina<br/>
Cardiff<br/>
CF14 6NQ
</p>

<p>If you would like a booking form sent in the post and are not on our distribution list (or have not received a booking form and think you should have), please use the <a href="/contact/">feedback form</a> to request one.  Please remember to to include your address so that we can post one.  If you are ordering 
a large number of booking forms, please include your telephone number so that we can verify the request.  </p>

"""
        h3.save()

        h4, x = orm['sitecontent.HtmlChunk'].objects.get_or_create(name="no_bookingform_yet")
        h4.html = """
<h2>Paper booking form</h2>

<p>There is no booking form for {{thisyear}} available yet online.  Booking forms are normally printed in January, and are distributed to all individuals who came on camp the previous year (sometimes via churches).  We try to make the booking form available online as a PDF file at about the same time, so that you can print your own.</p>

<p>An item will be added on the <a href="/news/">news page</a> when the booking form is available for download.</p>

<p>If you would like a booking form sent in the post and are not on our distribution list (or have not received a booking form and think you should have), please use the <a href="/contact/">feedback form</a> to request one.  Please remember to to include your address so that we can post one.  If you are ordering a large number of booking forms, please include your telephone number so that we can verify the request.  </p>
"""
        h4.save()

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
            'parent_item': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'child_links'", 'blank': 'True', 'null': 'True', 'to': "orm['sitecontent.MenuLink']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'visible': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        }
    }

    complete_apps = ['sitecontent']

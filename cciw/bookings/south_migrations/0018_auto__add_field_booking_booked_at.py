# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Booking.booked_at'
        db.add_column('bookings_booking', 'booked_at',
                      self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Booking.booked_at'
        db.delete_column('bookings_booking', 'booked_at')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'object_name': 'Permission'},
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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'user_set'", 'symmetrical': 'False', 'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'user_set'", 'symmetrical': 'False', 'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'bookings.booking': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Booking'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'bookings'", 'to': "orm['bookings.BookingAccount']"}),
            'address': ('django.db.models.fields.TextField', [], {}),
            'agreement': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'allergies': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'amount_due': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '2'}),
            'booked_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'booking_expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'camp': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'bookings'", 'to': "orm['cciwmain.Camp']"}),
            'church': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'contact_address': ('django.db.models.fields.TextField', [], {}),
            'contact_phone_number': ('django.db.models.fields.CharField', [], {'max_length': '22'}),
            'contact_post_code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'date_of_birth': ('django.db.models.fields.DateField', [], {}),
            'dietary_requirements': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'early_bird_discount': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'gp_address': ('django.db.models.fields.TextField', [], {}),
            'gp_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'gp_phone_number': ('django.db.models.fields.CharField', [], {'max_length': '22'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'illnesses': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'last_tetanus_injection': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'learning_difficulties': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'medical_card_number': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'phone_number': ('django.db.models.fields.CharField', [], {'max_length': '22', 'blank': 'True'}),
            'post_code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'price_type': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'regular_medication_required': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'serious_illness': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sex': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'shelved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'south_wales_transport': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'state': ('django.db.models.fields.IntegerField', [], {})
        },
        'bookings.bookingaccount': {
            'Meta': {'unique_together': "[('name', 'post_code'), ('name', 'email')]", 'object_name': 'BookingAccount'},
            'address': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'email_communication': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'first_login': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_payment_reminder': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'phone_number': ('django.db.models.fields.CharField', [], {'max_length': '22', 'blank': 'True'}),
            'post_code': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'share_phone_number': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'total_received': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'default': "'0.00'", 'decimal_places': '2'})
        },
        'bookings.manualpayment': {
            'Meta': {'object_name': 'ManualPayment'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['bookings.BookingAccount']"}),
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '2'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'payment_type': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'})
        },
        'bookings.payment': {
            'Meta': {'object_name': 'Payment'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['bookings.BookingAccount']"}),
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '2'}),
            'created': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'origin_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'origin_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'processed': ('django.db.models.fields.DateTimeField', [], {'null': 'True'})
        },
        'bookings.price': {
            'Meta': {'unique_together': "[('year', 'price_type')]", 'object_name': 'Price'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '2'}),
            'price_type': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'year': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'bookings.refundpayment': {
            'Meta': {'object_name': 'RefundPayment'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['bookings.BookingAccount']"}),
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '2'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'payment_type': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'})
        },
        'cciwmain.camp': {
            'Meta': {'unique_together': "(('year', 'number'),)", 'ordering': "['-year', 'number']", 'object_name': 'Camp'},
            'admins': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'camps_as_admin'", 'symmetrical': 'False', 'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'chaplain': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'camps_as_chaplain'", 'to': "orm['cciwmain.Person']", 'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'leaders': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'camps_as_leader'", 'symmetrical': 'False', 'to': "orm['cciwmain.Person']", 'null': 'True', 'blank': 'True'}),
            'max_campers': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '80'}),
            'max_female_campers': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '60'}),
            'max_male_campers': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '60'}),
            'maximum_age': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'minimum_age': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'number': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'officers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.User']", 'through': "orm['officers.Invitation']"}),
            'online_applications': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'previous_camp': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'next_camps'", 'to': "orm['cciwmain.Camp']", 'null': 'True', 'blank': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cciwmain.Site']"}),
            'south_wales_transport_available': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'year': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'cciwmain.person': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Person'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.User']", 'blank': 'True'})
        },
        'cciwmain.site': {
            'Meta': {'object_name': 'Site'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('django.db.models.fields.TextField', [], {}),
            'long_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'short_name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '25'}),
            'slug_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '25', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'ordering': "('name',)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'officers.invitation': {
            'Meta': {'unique_together': "(('officer', 'camp'),)", 'ordering': "('-camp__year', 'officer__first_name', 'officer__last_name')", 'object_name': 'Invitation'},
            'camp': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cciwmain.Camp']"}),
            'date_added': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'notes': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'officer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['bookings']
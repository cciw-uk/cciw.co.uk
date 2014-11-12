# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Booking.early_bird_discount'
        db.add_column('bookings_booking', 'early_bird_discount',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Booking.early_bird_discount'
        db.delete_column('bookings_booking', 'early_bird_discount')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'to': "orm['auth.Permission']", 'symmetrical': 'False'})
        },
        'auth.permission': {
            'Meta': {'object_name': 'Permission', 'unique_together': "(('content_type', 'codename'),)", 'ordering': "('content_type__app_label', 'content_type__model', 'codename')"},
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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'to': "orm['auth.Group']", 'symmetrical': 'False', 'related_name': "'user_set'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '30'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'to': "orm['auth.Permission']", 'symmetrical': 'False', 'related_name': "'user_set'"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'bookings.booking': {
            'Meta': {'object_name': 'Booking', 'ordering': "['-created']"},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['bookings.BookingAccount']", 'related_name': "'bookings'"}),
            'address': ('django.db.models.fields.TextField', [], {}),
            'agreement': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'allergies': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'amount_due': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '2'}),
            'booking_expires': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'null': 'True'}),
            'camp': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cciwmain.Camp']", 'related_name': "'bookings'"}),
            'church': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '100'}),
            'contact_address': ('django.db.models.fields.TextField', [], {}),
            'contact_phone_number': ('django.db.models.fields.CharField', [], {'max_length': '22'}),
            'contact_post_code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'date_of_birth': ('django.db.models.fields.DateField', [], {}),
            'dietary_requirements': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'early_bird_discount': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'email': ('django.db.models.fields.EmailField', [], {'blank': 'True', 'max_length': '75'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'gp_address': ('django.db.models.fields.TextField', [], {}),
            'gp_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'gp_phone_number': ('django.db.models.fields.CharField', [], {'max_length': '22'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'illnesses': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'last_tetanus_injection': ('django.db.models.fields.DateField', [], {'blank': 'True', 'null': 'True'}),
            'learning_difficulties': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'medical_card_number': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'phone_number': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '22'}),
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
            'Meta': {'object_name': 'BookingAccount', 'unique_together': "[('name', 'post_code'), ('name', 'email')]"},
            'address': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'blank': 'True', 'unique': 'True', 'max_length': '75', 'null': 'True'}),
            'email_communication': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'first_login': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'null': 'True'}),
            'last_payment_reminder': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '100', 'null': 'True'}),
            'phone_number': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '22'}),
            'post_code': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '10', 'null': 'True'}),
            'share_phone_number': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'total_received': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '2', 'default': "'0.00'"})
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
            'Meta': {'object_name': 'Price', 'unique_together': "[('year', 'price_type')]"},
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
            'Meta': {'object_name': 'Camp', 'unique_together': "(('year', 'number'),)", 'ordering': "['-year', 'number']"},
            'admins': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'to': "orm['auth.User']", 'symmetrical': 'False', 'related_name': "'camps_as_admin'", 'null': 'True'}),
            'chaplain': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'to': "orm['cciwmain.Person']", 'related_name': "'camps_as_chaplain'", 'null': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'leaders': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'to': "orm['cciwmain.Person']", 'symmetrical': 'False', 'related_name': "'camps_as_leader'", 'null': 'True'}),
            'max_campers': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '80'}),
            'max_female_campers': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '60'}),
            'max_male_campers': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '60'}),
            'maximum_age': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'minimum_age': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'number': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'officers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'through': "orm['officers.Invitation']"}),
            'online_applications': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'previous_camp': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'to': "orm['cciwmain.Camp']", 'related_name': "'next_camps'", 'null': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cciwmain.Site']"}),
            'south_wales_transport_available': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'year': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'cciwmain.person': {
            'Meta': {'object_name': 'Person', 'ordering': "('name',)"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'to': "orm['auth.User']", 'symmetrical': 'False'})
        },
        'cciwmain.site': {
            'Meta': {'object_name': 'Site'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('django.db.models.fields.TextField', [], {}),
            'long_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'short_name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '25'}),
            'slug_name': ('django.db.models.fields.SlugField', [], {'blank': 'True', 'unique': 'True', 'max_length': '25'})
        },
        'contenttypes.contenttype': {
            'Meta': {'object_name': 'ContentType', 'unique_together': "(('app_label', 'model'),)", 'ordering': "('name',)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'officers.invitation': {
            'Meta': {'object_name': 'Invitation', 'unique_together': "(('officer', 'camp'),)", 'ordering': "('-camp__year', 'officer__first_name', 'officer__last_name')"},
            'camp': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cciwmain.Camp']"}),
            'date_added': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'notes': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '255'}),
            'officer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['bookings']
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Deleting field 'BookingAccount.activated'
        db.delete_column('bookings_bookingaccount', 'activated')

        # Adding field 'BookingAccount.first_login'
        db.add_column('bookings_bookingaccount', 'first_login', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True), keep_default=False)

        # Adding field 'BookingAccount.last_login'
        db.add_column('bookings_bookingaccount', 'last_login', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True), keep_default=False)


    def backwards(self, orm):

        # Adding field 'BookingAccount.activated'
        db.add_column('bookings_bookingaccount', 'activated', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True), keep_default=False)

        # Deleting field 'BookingAccount.first_login'
        db.delete_column('bookings_bookingaccount', 'first_login')

        # Deleting field 'BookingAccount.last_login'
        db.delete_column('bookings_bookingaccount', 'last_login')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
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
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'bookings.booking': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Booking'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'bookings'", 'to': "orm['bookings.BookingAccount']"}),
            'address': ('django.db.models.fields.TextField', [], {}),
            'agreement': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'allergies': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'amount_due': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '2'}),
            'booking_expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'camp': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'bookings'", 'to': "orm['cciwmain.Camp']"}),
            'church': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'contact_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'contact_phone_number': ('django.db.models.fields.CharField', [], {'max_length': '22'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'date_of_birth': ('django.db.models.fields.DateField', [], {}),
            'dietary_requirements': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'gp_address': ('django.db.models.fields.TextField', [], {}),
            'gp_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'gp_phone_number': ('django.db.models.fields.CharField', [], {'max_length': '22'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'illnesses': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'last_tetanus_injection': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'learning_difficulties': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'medical_card_number': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
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
            'Meta': {'object_name': 'BookingAccount'},
            'address': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '75', 'blank': 'True'}),
            'first_login': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'phone_number': ('django.db.models.fields.CharField', [], {'max_length': '22', 'blank': 'True'}),
            'post_code': ('django.db.models.fields.CharField', [], {'max_length': '10', 'blank': 'True'}),
            'share_phone_number': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'total_received': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '10', 'decimal_places': '2'})
        },
        'bookings.price': {
            'Meta': {'unique_together': "(['year', 'price_type'],)", 'object_name': 'Price'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '2'}),
            'price_type': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'year': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'cciwmain.camp': {
            'Meta': {'ordering': "['-year', 'number']", 'unique_together': "(('year', 'number'),)", 'object_name': 'Camp'},
            'admins': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'camps_as_admin'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'chaplain': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'camps_as_chaplain'", 'null': 'True', 'to': "orm['cciwmain.Person']"}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'leaders': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'camps_as_leader'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['cciwmain.Person']"}),
            'max_campers': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '80'}),
            'max_female_campers': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '60'}),
            'max_male_campers': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '60'}),
            'maximum_age': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'minimum_age': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'number': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'officers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'through': "orm['officers.Invitation']", 'symmetrical': 'False'}),
            'online_applications': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'previous_camp': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'next_camps'", 'null': 'True', 'to': "orm['cciwmain.Camp']"}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cciwmain.Site']"}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'year': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
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
            'short_name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': "'25'"}),
            'slug_name': ('django.db.models.fields.SlugField', [], {'db_index': 'True', 'unique': 'True', 'max_length': "'25'", 'blank': 'True'})
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

    complete_apps = ['bookings']

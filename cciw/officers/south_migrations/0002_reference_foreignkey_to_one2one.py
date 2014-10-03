# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'ReferenceForm.reference_info'
        db.alter_column('officers_referenceform', 'reference_info_id', self.gf('django.db.models.fields.related.OneToOneField')(unique=True, to=orm['officers.Reference']))

        # Adding unique constraint on 'ReferenceForm', fields ['reference_info']
        db.create_unique('officers_referenceform', ['reference_info_id'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'ReferenceForm', fields ['reference_info']
        db.delete_unique('officers_referenceform', ['reference_info_id'])

        # Changing field 'ReferenceForm.reference_info'
        db.alter_column('officers_referenceform', 'reference_info_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['officers.Reference']))


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
            'Meta': {'ordering': "['-year', 'number']", 'object_name': 'Camp'},
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
        'officers.application': {
            'Meta': {'ordering': "('-camp__year', 'officer__first_name', 'officer__last_name', 'camp__number')", 'object_name': 'Application'},
            'address2_address': ('cciw.officers.fields.AddressField', [], {'blank': 'True'}),
            'address2_from': ('cciw.officers.fields.YyyyMmField', [], {'max_length': '7', 'blank': 'True'}),
            'address2_to': ('cciw.officers.fields.YyyyMmField', [], {'max_length': '7', 'blank': 'True'}),
            'address3_address': ('cciw.officers.fields.AddressField', [], {'blank': 'True'}),
            'address3_from': ('cciw.officers.fields.YyyyMmField', [], {'max_length': '7', 'blank': 'True'}),
            'address3_to': ('cciw.officers.fields.YyyyMmField', [], {'max_length': '7', 'blank': 'True'}),
            'address_country': ('cciw.officers.fields.RequiredCharField', [], {'max_length': '30', 'blank': 'True'}),
            'address_county': ('cciw.officers.fields.RequiredCharField', [], {'max_length': '30', 'blank': 'True'}),
            'address_email': ('cciw.officers.fields.RequiredEmailField', [], {'max_length': '75', 'blank': 'True'}),
            'address_firstline': ('cciw.officers.fields.RequiredCharField', [], {'max_length': '40', 'blank': 'True'}),
            'address_mobile': ('django.db.models.fields.CharField', [], {'max_length': '22', 'blank': 'True'}),
            'address_postcode': ('cciw.officers.fields.RequiredCharField', [], {'max_length': '10', 'blank': 'True'}),
            'address_since': ('cciw.officers.fields.RequiredYyyyMmField', [], {'max_length': '7', 'blank': 'True'}),
            'address_tel': ('cciw.officers.fields.RequiredCharField', [], {'max_length': '22', 'blank': 'True'}),
            'address_town': ('cciw.officers.fields.RequiredCharField', [], {'max_length': '60', 'blank': 'True'}),
            'allegation_declaration': ('cciw.officers.fields.RequiredNullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'birth_date': ('cciw.officers.fields.RequiredDateField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'birth_place': ('cciw.officers.fields.RequiredCharField', [], {'max_length': '60', 'blank': 'True'}),
            'camp': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cciwmain.Camp']", 'null': 'True'}),
            'christian_experience': ('cciw.officers.fields.RequiredTextField', [], {'blank': 'True'}),
            'concern_declaration': ('cciw.officers.fields.RequiredNullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'concern_details': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'court_declaration': ('cciw.officers.fields.RequiredNullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'court_details': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'crb_check_consent': ('cciw.officers.fields.RequiredNullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'crime_declaration': ('cciw.officers.fields.RequiredNullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'crime_details': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date_submitted': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'employer1_from': ('cciw.officers.fields.YyyyMmField', [], {'max_length': '7', 'blank': 'True'}),
            'employer1_job': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'employer1_leaving': ('django.db.models.fields.CharField', [], {'max_length': '150', 'blank': 'True'}),
            'employer1_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'employer1_to': ('cciw.officers.fields.YyyyMmField', [], {'max_length': '7', 'blank': 'True'}),
            'employer2_from': ('cciw.officers.fields.YyyyMmField', [], {'max_length': '7', 'blank': 'True'}),
            'employer2_job': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'employer2_leaving': ('django.db.models.fields.CharField', [], {'max_length': '150', 'blank': 'True'}),
            'employer2_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'employer2_to': ('cciw.officers.fields.YyyyMmField', [], {'max_length': '7', 'blank': 'True'}),
            'finished': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'full_maiden_name': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'full_name': ('cciw.officers.fields.RequiredCharField', [], {'max_length': '60', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'illness_details': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'officer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'blank': 'True'}),
            'referee1_address': ('cciw.officers.fields.RequiredAddressField', [], {'blank': 'True'}),
            'referee1_email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'referee1_mobile': ('django.db.models.fields.CharField', [], {'max_length': '22', 'blank': 'True'}),
            'referee1_name': ('cciw.officers.fields.RequiredCharField', [], {'max_length': '60', 'blank': 'True'}),
            'referee1_tel': ('django.db.models.fields.CharField', [], {'max_length': '22', 'blank': 'True'}),
            'referee2_address': ('cciw.officers.fields.RequiredAddressField', [], {'blank': 'True'}),
            'referee2_email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'referee2_mobile': ('django.db.models.fields.CharField', [], {'max_length': '22', 'blank': 'True'}),
            'referee2_name': ('cciw.officers.fields.RequiredCharField', [], {'max_length': '60', 'blank': 'True'}),
            'referee2_tel': ('django.db.models.fields.CharField', [], {'max_length': '22', 'blank': 'True'}),
            'relevant_illness': ('cciw.officers.fields.RequiredNullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'youth_experience': ('cciw.officers.fields.RequiredTextField', [], {'blank': 'True'}),
            'youth_work_declined': ('cciw.officers.fields.RequiredNullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'youth_work_declined_details': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'officers.invitation': {
            'Meta': {'ordering': "('-camp__year', 'officer__first_name', 'officer__last_name')", 'unique_together': "(('officer', 'camp'),)", 'object_name': 'Invitation'},
            'camp': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cciwmain.Camp']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'officer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'officers.reference': {
            'Meta': {'ordering': "('application__camp__year', 'application__officer__first_name', 'application__officer__last_name', 'application__camp__number', 'referee_number')", 'unique_together': "(('application', 'referee_number'),)", 'object_name': 'Reference'},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['officers.Application']"}),
            'comments': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'received': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'referee_number': ('django.db.models.fields.SmallIntegerField', [], {}),
            'requested': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'officers.referenceform': {
            'Meta': {'object_name': 'ReferenceForm'},
            'capability_children': ('django.db.models.fields.TextField', [], {}),
            'capacity_known': ('django.db.models.fields.TextField', [], {}),
            'character': ('django.db.models.fields.TextField', [], {}),
            'comments': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'concerns': ('django.db.models.fields.TextField', [], {}),
            'date_created': ('django.db.models.fields.DateField', [], {}),
            'how_long_known': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'known_offences': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'known_offences_details': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'referee_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'reference_info': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'_reference_form'", 'unique': 'True', 'to': "orm['officers.Reference']"})
        }
    }

    complete_apps = ['officers']

# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting model 'ConfirmToken'
        db.delete_table('utils_confirmtoken')


    def backwards(self, orm):
        
        # Adding model 'ConfirmToken'
        db.create_table('utils_confirmtoken', (
            ('objdata', self.gf('django.db.models.fields.TextField')()),
            ('expires', self.gf('django.db.models.fields.DateTimeField')()),
            ('token', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('action_type', self.gf('django.db.models.fields.CharField')(max_length='50')),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('utils', ['ConfirmToken'])


    models = {
        
    }

    complete_apps = ['utils']

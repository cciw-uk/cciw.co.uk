# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Permission'
        db.create_table('cciwmain_permission', (
            ('id', self.gf('django.db.models.fields.PositiveSmallIntegerField')(primary_key=True)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=40)),
        ))
        db.send_create_signal('cciwmain', ['Permission'])

        # Adding model 'Member'
        db.create_table('cciwmain_member', (
            ('user_name', self.gf('django.db.models.fields.CharField')(max_length=30, primary_key=True)),
            ('real_name', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75)),
            ('password', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('date_joined', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('last_seen', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('show_email', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('message_option', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=1)),
            ('comments', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('moderated', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=0)),
            ('hidden', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('banned', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('icon', self.gf('django.db.models.fields.files.ImageField')(max_length=100, blank=True)),
            ('dummy_member', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('cciwmain', ['Member'])

        # Adding M2M table for field permissions on 'Member'
        db.create_table('cciwmain_member_permissions', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('member', models.ForeignKey(orm['cciwmain.member'], null=False)),
            ('permission', models.ForeignKey(orm['cciwmain.permission'], null=False))
        ))
        db.create_unique('cciwmain_member_permissions', ['member_id', 'permission_id'])

        # Adding model 'Award'
        db.create_table('cciwmain_award', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('value', self.gf('django.db.models.fields.SmallIntegerField')()),
            ('year', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=100)),
        ))
        db.send_create_signal('cciwmain', ['Award'])

        # Adding model 'PersonalAward'
        db.create_table('cciwmain_personalaward', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('reason', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('date_awarded', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('award', self.gf('django.db.models.fields.related.ForeignKey')(related_name='personal_awards', to=orm['cciwmain.Award'])),
            ('member', self.gf('django.db.models.fields.related.ForeignKey')(related_name='personal_awards', to=orm['cciwmain.Member'])),
        ))
        db.send_create_signal('cciwmain', ['PersonalAward'])

        # Adding model 'Message'
        db.create_table('cciwmain_message', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('from_member', self.gf('django.db.models.fields.related.ForeignKey')(related_name='messages_sent', to=orm['cciwmain.Member'])),
            ('to_member', self.gf('django.db.models.fields.related.ForeignKey')(related_name='messages_received', to=orm['cciwmain.Member'])),
            ('time', self.gf('django.db.models.fields.DateTimeField')()),
            ('text', self.gf('django.db.models.fields.TextField')()),
            ('box', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
        ))
        db.send_create_signal('cciwmain', ['Message'])

        # Adding model 'Site'
        db.create_table('cciwmain_site', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('short_name', self.gf('django.db.models.fields.CharField')(max_length='25', unique=True)),
            ('slug_name', self.gf('django.db.models.fields.SlugField')(db_index=True, max_length='25', unique=True, blank=True)),
            ('long_name', self.gf('django.db.models.fields.CharField')(max_length='50')),
            ('info', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('cciwmain', ['Site'])

        # Adding model 'Person'
        db.create_table('cciwmain_person', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=40)),
            ('info', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('cciwmain', ['Person'])

        # Adding M2M table for field users on 'Person'
        db.create_table('cciwmain_person_users', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('person', models.ForeignKey(orm['cciwmain.person'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('cciwmain_person_users', ['person_id', 'user_id'])

        # Adding model 'Camp'
        db.create_table('cciwmain_camp', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('year', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('number', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('age', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('start_date', self.gf('django.db.models.fields.DateField')()),
            ('end_date', self.gf('django.db.models.fields.DateField')()),
            ('previous_camp', self.gf('django.db.models.fields.related.ForeignKey')(related_name='next_camps', blank=True, null=True, to=orm['cciwmain.Camp'])),
            ('chaplain', self.gf('django.db.models.fields.related.ForeignKey')(related_name='camps_as_chaplain', blank=True, null=True, to=orm['cciwmain.Person'])),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['cciwmain.Site'])),
            ('online_applications', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('cciwmain', ['Camp'])

        # Adding M2M table for field leaders on 'Camp'
        db.create_table('cciwmain_camp_leaders', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('camp', models.ForeignKey(orm['cciwmain.camp'], null=False)),
            ('person', models.ForeignKey(orm['cciwmain.person'], null=False))
        ))
        db.create_unique('cciwmain_camp_leaders', ['camp_id', 'person_id'])

        # Adding M2M table for field admins on 'Camp'
        db.create_table('cciwmain_camp_admins', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('camp', models.ForeignKey(orm['cciwmain.camp'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('cciwmain_camp_admins', ['camp_id', 'user_id'])

        # Adding model 'Poll'
        db.create_table('cciwmain_poll', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('intro_text', self.gf('django.db.models.fields.CharField')(max_length=400, blank=True)),
            ('outro_text', self.gf('django.db.models.fields.CharField')(max_length=400, blank=True)),
            ('voting_starts', self.gf('django.db.models.fields.DateTimeField')()),
            ('voting_ends', self.gf('django.db.models.fields.DateTimeField')()),
            ('rules', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('rule_parameter', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=1)),
            ('have_vote_info', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='polls_created', to=orm['cciwmain.Member'])),
        ))
        db.send_create_signal('cciwmain', ['Poll'])

        # Adding model 'PollOption'
        db.create_table('cciwmain_polloption', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('text', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('total', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('poll', self.gf('django.db.models.fields.related.ForeignKey')(related_name='poll_options', to=orm['cciwmain.Poll'])),
            ('listorder', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
        ))
        db.send_create_signal('cciwmain', ['PollOption'])

        # Adding model 'VoteInfo'
        db.create_table('cciwmain_voteinfo', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('poll_option', self.gf('django.db.models.fields.related.ForeignKey')(related_name='votes', to=orm['cciwmain.PollOption'])),
            ('member', self.gf('django.db.models.fields.related.ForeignKey')(related_name='poll_votes', to=orm['cciwmain.Member'])),
            ('date', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal('cciwmain', ['VoteInfo'])

        # Adding model 'Forum'
        db.create_table('cciwmain_forum', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('open', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('location', self.gf('django.db.models.fields.CharField')(max_length=50, unique=True, db_index=True)),
        ))
        db.send_create_signal('cciwmain', ['Forum'])

        # Adding model 'NewsItem'
        db.create_table('cciwmain_newsitem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='news_items_created', to=orm['cciwmain.Member'])),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')()),
            ('summary', self.gf('django.db.models.fields.TextField')()),
            ('full_item', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('subject', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal('cciwmain', ['NewsItem'])

        # Adding model 'Topic'
        db.create_table('cciwmain_topic', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('subject', self.gf('django.db.models.fields.CharField')(max_length=240)),
            ('started_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='topics_started', to=orm['cciwmain.Member'])),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('open', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('hidden', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('approved', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('checked_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='topics_checked', blank=True, null=True, to=orm['auth.User'])),
            ('needs_approval', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('news_item', self.gf('django.db.models.fields.related.ForeignKey')(related_name='topics', blank=True, null=True, to=orm['cciwmain.NewsItem'])),
            ('poll', self.gf('django.db.models.fields.related.ForeignKey')(related_name='topics', blank=True, null=True, to=orm['cciwmain.Poll'])),
            ('forum', self.gf('django.db.models.fields.related.ForeignKey')(related_name='topics', to=orm['cciwmain.Forum'])),
            ('last_post_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('last_post_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='topics_with_last_post', blank=True, null=True, to=orm['cciwmain.Member'])),
            ('post_count', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=0)),
        ))
        db.send_create_signal('cciwmain', ['Topic'])

        # Adding model 'Gallery'
        db.create_table('cciwmain_gallery', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('location', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('needs_approval', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('cciwmain', ['Gallery'])

        # Adding model 'Photo'
        db.create_table('cciwmain_photo', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('open', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('hidden', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('filename', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('gallery', self.gf('django.db.models.fields.related.ForeignKey')(related_name='photos', to=orm['cciwmain.Gallery'])),
            ('checked_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='photos_checked', blank=True, null=True, to=orm['auth.User'])),
            ('approved', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('needs_approval', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('last_post_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('last_post_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='photos_with_last_post', blank=True, null=True, to=orm['cciwmain.Member'])),
            ('post_count', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=0)),
        ))
        db.send_create_signal('cciwmain', ['Photo'])

        # Adding model 'Post'
        db.create_table('cciwmain_post', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('posted_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='posts', to=orm['cciwmain.Member'])),
            ('subject', self.gf('django.db.models.fields.CharField')(max_length=240, blank=True)),
            ('message', self.gf('django.db.models.fields.TextField')()),
            ('posted_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('hidden', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('approved', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('checked_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='checked_post', blank=True, null=True, to=orm['auth.User'])),
            ('needs_approval', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('photo', self.gf('django.db.models.fields.related.ForeignKey')(related_name='posts', blank=True, null=True, to=orm['cciwmain.Photo'])),
            ('topic', self.gf('django.db.models.fields.related.ForeignKey')(related_name='posts', blank=True, null=True, to=orm['cciwmain.Topic'])),
        ))
        db.send_create_signal('cciwmain', ['Post'])

        # Adding model 'MenuLink'
        db.create_table('cciwmain_menulink', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('url', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('extra_title', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('listorder', self.gf('django.db.models.fields.SmallIntegerField')()),
            ('visible', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('parent_item', self.gf('django.db.models.fields.related.ForeignKey')(related_name='child_links', blank=True, null=True, to=orm['cciwmain.MenuLink'])),
        ))
        db.send_create_signal('cciwmain', ['MenuLink'])

        # Adding model 'HtmlChunk'
        db.create_table('cciwmain_htmlchunk', (
            ('name', self.gf('django.db.models.fields.SlugField')(max_length=50, primary_key=True, db_index=True)),
            ('html', self.gf('django.db.models.fields.TextField')()),
            ('menu_link', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['cciwmain.MenuLink'], null=True, blank=True)),
            ('page_title', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
        ))
        db.send_create_signal('cciwmain', ['HtmlChunk'])


    def backwards(self, orm):
        
        # Deleting model 'Permission'
        db.delete_table('cciwmain_permission')

        # Deleting model 'Member'
        db.delete_table('cciwmain_member')

        # Removing M2M table for field permissions on 'Member'
        db.delete_table('cciwmain_member_permissions')

        # Deleting model 'Award'
        db.delete_table('cciwmain_award')

        # Deleting model 'PersonalAward'
        db.delete_table('cciwmain_personalaward')

        # Deleting model 'Message'
        db.delete_table('cciwmain_message')

        # Deleting model 'Site'
        db.delete_table('cciwmain_site')

        # Deleting model 'Person'
        db.delete_table('cciwmain_person')

        # Removing M2M table for field users on 'Person'
        db.delete_table('cciwmain_person_users')

        # Deleting model 'Camp'
        db.delete_table('cciwmain_camp')

        # Removing M2M table for field leaders on 'Camp'
        db.delete_table('cciwmain_camp_leaders')

        # Removing M2M table for field admins on 'Camp'
        db.delete_table('cciwmain_camp_admins')

        # Deleting model 'Poll'
        db.delete_table('cciwmain_poll')

        # Deleting model 'PollOption'
        db.delete_table('cciwmain_polloption')

        # Deleting model 'VoteInfo'
        db.delete_table('cciwmain_voteinfo')

        # Deleting model 'Forum'
        db.delete_table('cciwmain_forum')

        # Deleting model 'NewsItem'
        db.delete_table('cciwmain_newsitem')

        # Deleting model 'Topic'
        db.delete_table('cciwmain_topic')

        # Deleting model 'Gallery'
        db.delete_table('cciwmain_gallery')

        # Deleting model 'Photo'
        db.delete_table('cciwmain_photo')

        # Deleting model 'Post'
        db.delete_table('cciwmain_post')

        # Deleting model 'MenuLink'
        db.delete_table('cciwmain_menulink')

        # Deleting model 'HtmlChunk'
        db.delete_table('cciwmain_htmlchunk')


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
        'cciwmain.award': {
            'Meta': {'ordering': "('-year', 'name')", 'object_name': 'Award'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'value': ('django.db.models.fields.SmallIntegerField', [], {}),
            'year': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
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
            'online_applications': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'previous_camp': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'next_camps'", 'blank': 'True', 'null': 'True', 'to': "orm['cciwmain.Camp']"}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cciwmain.Site']"}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'year': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'cciwmain.forum': {
            'Meta': {'object_name': 'Forum'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '50', 'unique': 'True', 'db_index': 'True'}),
            'open': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'cciwmain.gallery': {
            'Meta': {'ordering': "('-location',)", 'object_name': 'Gallery'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'needs_approval': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'cciwmain.htmlchunk': {
            'Meta': {'object_name': 'HtmlChunk'},
            'html': ('django.db.models.fields.TextField', [], {}),
            'menu_link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cciwmain.MenuLink']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True', 'db_index': 'True'}),
            'page_title': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'})
        },
        'cciwmain.member': {
            'Meta': {'ordering': "('user_name',)", 'object_name': 'Member'},
            'banned': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'comments': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'dummy_member': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'icon': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'last_seen': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'message_option': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1'}),
            'moderated': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'member_with_permission'", 'blank': 'True', 'null': 'True', 'to': "orm['cciwmain.Permission']"}),
            'real_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'show_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'primary_key': 'True'})
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
        'cciwmain.message': {
            'Meta': {'ordering': "('-time',)", 'object_name': 'Message'},
            'box': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'from_member': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages_sent'", 'to': "orm['cciwmain.Member']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'time': ('django.db.models.fields.DateTimeField', [], {}),
            'to_member': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages_received'", 'to': "orm['cciwmain.Member']"})
        },
        'cciwmain.newsitem': {
            'Meta': {'ordering': "('-created_at',)", 'object_name': 'NewsItem'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'news_items_created'", 'to': "orm['cciwmain.Member']"}),
            'full_item': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'summary': ('django.db.models.fields.TextField', [], {})
        },
        'cciwmain.permission': {
            'Meta': {'ordering': "('id',)", 'object_name': 'Permission'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'id': ('django.db.models.fields.PositiveSmallIntegerField', [], {'primary_key': 'True'})
        },
        'cciwmain.person': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Person'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'cciwmain.personalaward': {
            'Meta': {'ordering': "('date_awarded',)", 'object_name': 'PersonalAward'},
            'award': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'personal_awards'", 'to': "orm['cciwmain.Award']"}),
            'date_awarded': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'member': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'personal_awards'", 'to': "orm['cciwmain.Member']"}),
            'reason': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cciwmain.photo': {
            'Meta': {'object_name': 'Photo'},
            'approved': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'checked_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'photos_checked'", 'blank': 'True', 'null': 'True', 'to': "orm['auth.User']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'gallery': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'photos'", 'to': "orm['cciwmain.Gallery']"}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_post_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'photos_with_last_post'", 'blank': 'True', 'null': 'True', 'to': "orm['cciwmain.Member']"}),
            'needs_approval': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'open': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'post_count': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'})
        },
        'cciwmain.poll': {
            'Meta': {'ordering': "('title',)", 'object_name': 'Poll'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polls_created'", 'to': "orm['cciwmain.Member']"}),
            'have_vote_info': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'intro_text': ('django.db.models.fields.CharField', [], {'max_length': '400', 'blank': 'True'}),
            'outro_text': ('django.db.models.fields.CharField', [], {'max_length': '400', 'blank': 'True'}),
            'rule_parameter': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1'}),
            'rules': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'voting_ends': ('django.db.models.fields.DateTimeField', [], {}),
            'voting_starts': ('django.db.models.fields.DateTimeField', [], {})
        },
        'cciwmain.polloption': {
            'Meta': {'ordering': "('poll', 'listorder')", 'object_name': 'PollOption'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'listorder': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'poll': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'poll_options'", 'to': "orm['cciwmain.Poll']"}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'total': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'cciwmain.post': {
            'Meta': {'ordering': "('id',)", 'object_name': 'Post'},
            'approved': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'checked_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'checked_post'", 'blank': 'True', 'null': 'True', 'to': "orm['auth.User']"}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'needs_approval': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'photo': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'blank': 'True', 'null': 'True', 'to': "orm['cciwmain.Photo']"}),
            'posted_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'posted_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'to': "orm['cciwmain.Member']"}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '240', 'blank': 'True'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'blank': 'True', 'null': 'True', 'to': "orm['cciwmain.Topic']"})
        },
        'cciwmain.site': {
            'Meta': {'object_name': 'Site'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('django.db.models.fields.TextField', [], {}),
            'long_name': ('django.db.models.fields.CharField', [], {'max_length': "'50'"}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': "'25'", 'unique': 'True'}),
            'slug_name': ('django.db.models.fields.SlugField', [], {'db_index': 'True', 'max_length': "'25'", 'unique': 'True', 'blank': 'True'})
        },
        'cciwmain.topic': {
            'Meta': {'ordering': "('-started_by',)", 'object_name': 'Topic'},
            'approved': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'checked_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topics_checked'", 'blank': 'True', 'null': 'True', 'to': "orm['auth.User']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'forum': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topics'", 'to': "orm['cciwmain.Forum']"}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_post_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_post_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topics_with_last_post'", 'blank': 'True', 'null': 'True', 'to': "orm['cciwmain.Member']"}),
            'needs_approval': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'news_item': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topics'", 'blank': 'True', 'null': 'True', 'to': "orm['cciwmain.NewsItem']"}),
            'open': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'poll': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topics'", 'blank': 'True', 'null': 'True', 'to': "orm['cciwmain.Poll']"}),
            'post_count': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'started_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'topics_started'", 'to': "orm['cciwmain.Member']"}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '240'})
        },
        'cciwmain.voteinfo': {
            'Meta': {'object_name': 'VoteInfo'},
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'member': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'poll_votes'", 'to': "orm['cciwmain.Member']"}),
            'poll_option': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'votes'", 'to': "orm['cciwmain.PollOption']"})
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
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'officer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['cciwmain']

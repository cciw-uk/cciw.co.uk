from django.conf.urls.defaults import patterns

urlpatterns = patterns('cciw.officers.views',
    (r'^$', 'index'),
    (r'^applications/$', 'applications'),
    (r'^view-application/$', 'view_application'),
    (r'^update-email/(?P<username>.*)/$', 'update_email'),
    (r'^leaders/$', 'leaders_index'),
    (r'^leaders/applications/(?P<year>\d{4})/(?P<number>\d+)/$', 'manage_applications'),
    (r'^leaders/references/(?P<year>\d{4})/(?P<number>\d+)/$', 'manage_references'),
    (r'^leaders/officer-list/(?P<year>\d{4})/(?P<number>\d+)/$', 'officer_list'),
    (r'^leaders/request-reference/$', 'request_reference'),
    (r'^leaders/reference/(?P<ref_id>\d+)/$', 'view_reference'),
    (r'^leaders/edit-reference/(?P<ref_id>\d+)/$', 'edit_reference_form_manually'),
    (r'^ref/(?P<ref_id>\d+)-(?P<prev_ref_id>\d*)-(?P<hash>.*)/$', 'create_reference_form'),
    (r'^ref/thanks/$', 'create_reference_thanks'),
    (r'^add-officer/$', 'create_officer'),
)

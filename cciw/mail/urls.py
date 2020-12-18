from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^ses-incoming-notification/$', views.ses_incoming_notification, name='cciw-ses-incoming-notification'),
    url(r'^ses-bounce/$', views.ses_bounce_notification, name='cciw-ses-bounce'),
]

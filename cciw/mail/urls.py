from . import views
from django.conf.urls import url

urlpatterns = [
    url(r'^mailgun-incoming-mime/$', views.mailgun_incoming, name='cciw-mailgun-incoming'),
    url(r'^mailgun-bounce/$', views.mailgun_bounce_notification, name='cciw-mailgun-bounce'),
    url(r'^mailgun-drop/$', views.mailgun_drop_notification, name='cciw-mailgun-drop'),
    url(r'^mailgun-deliver/$', views.mailgun_deliver_notification, name='cciw-mailgun-deliver'),
]

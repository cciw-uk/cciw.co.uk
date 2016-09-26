from . import views
from django.conf.urls import url

urlpatterns = [
    url(r'^mailgun-incoming-mime/$', views.mailgun_incoming, name='cciw-mailgun-incoming'),
]

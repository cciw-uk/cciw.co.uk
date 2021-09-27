from django.urls import path

from . import views

urlpatterns = [
    path(r"ses-incoming-notification/", views.ses_incoming_notification, name="cciw-ses-incoming-notification"),
    path(r"ses-bounce/", views.ses_bounce_notification, name="cciw-ses-bounce"),
]

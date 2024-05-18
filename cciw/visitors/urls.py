from django.urls import path

from . import views

urlpatterns = [
    path("log/", views.create_visitor_log, name="cciw-visitors-create_log"),
]

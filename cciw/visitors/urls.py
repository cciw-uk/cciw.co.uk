from django.urls import path

from . import views

urlpatterns = [
    path("log/<str:token>/", views.create_visitor_log, name="cciw-visitors-create_log"),
]

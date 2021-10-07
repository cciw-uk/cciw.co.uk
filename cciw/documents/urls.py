from django.urls import path

from . import views

urlpatterns = [
    path("download/<str:app_label>/<str:model_name>/<int:id>/", views.download, name="documents-download"),
]

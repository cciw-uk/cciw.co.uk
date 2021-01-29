from django.urls import path

from . import views

urlpatterns = [
    path('', views.contact_us, name="cciw-contact_us-send"),
    path('done/', views.contact_us_done, name="cciw-contact_us-done"),
    path(r'view/<int:message_id>/', views.view_message, name="cciw-contact_us-view"),
]

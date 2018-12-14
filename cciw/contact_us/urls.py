from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.contact_us, name="cciw-contact_us-send"),
    url(r'^done/$', views.contact_us_done, name="cciw-contact_us-done"),
    url(r'^view/(\d+)/$', views.view_message, name="cciw-contact_us-view"),
]

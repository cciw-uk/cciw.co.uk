from django.urls import path

from cciw.cciwmain.views import camps as camp_views
from cciw.cciwmain.views import sites as sites_views
from cciw.donations import views as donations_views
from cciw.sitecontent import views as sitecontent_views

from . import views

urlpatterns = [
    # Camps
    path("thisyear/", camp_views.thisyear, name="cciw-cciwmain-thisyear"),
    path("camps/", camp_views.index, name="cciw-cciwmain-camps_index"),
    path("camps/<yyyy:year>/", camp_views.index, name="cciw-cciwmain-camps_year_index"),
    path("camps/<yyyy:year>/<slug:slug>/", camp_views.detail, name="cciw-cciwmain-camps_detail"),
    # Sites
    path("sites/", sites_views.index, name="cciw-cciwmain-sites_index"),
    path("sites/<slug:slug>/", sites_views.detail, name="cciw-cciwmain-sites_detail"),
    path("404/", views.show404, name="cciw-404"),
    path("500/", views.show500, name="cciw-500"),
    # Site content
    path("data-retention-policy/", sitecontent_views.data_retention_policy, name="cciw-cciwmain-data_retention_policy"),
    path("donate/", donations_views.donate, name="cciw-donations-donate"),
    path("donate-done/", donations_views.donate_done, name="cciw-donations-donate_done"),
    path("", sitecontent_views.home, name="cciw-cciwmain-sitecontent_home"),
    # Fallback -- allows any other URL to be defined as arbitary pages.
    # htmlchunk.find will throw a 404 for any URL not defined.
    path("<path:path>/", sitecontent_views.find, name="cciw-cciwmain-sitecontent_find"),
]

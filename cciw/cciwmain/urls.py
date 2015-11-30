from django.conf.urls import url

from cciw.cciwmain.views import camps as camp_views
from cciw.cciwmain.views import sites as sites_views
from cciw.cciwmain.views import misc as misc_views
from cciw.sitecontent import views as sitecontent_views


urlpatterns = [
    # Camps
    url(r'^thisyear/$', camp_views.thisyear, name="cciw-cciwmain-thisyear"),
    url(r'^camps/$', camp_views.index, name="cciw-cciwmain-camps_index"),
    url(r'^camps/(?P<year>\d{4})/?$', camp_views.index, name="cciw-cciwmain-camps_year_index"),
    url(r'^camps/(?P<year>\d{4})/(?P<number>\d+)/$', camp_views.detail, name="cciw-cciwmain-camps_detail"),

    # Sites
    url(r'^sites/$', sites_views.index, name="cciw-cciwmain-sites_index"),
    url(r'^sites/(?P<slug>.*)/$', sites_views.detail, name="cciw-cciwmain-sites_detail"),

    # ContactUs form
    url(r'^contact/$', misc_views.contact_us, name="cciw-cciwmain-contact_us"),
    url(r'^contact/done/$', misc_views.contact_us_done, name="cciw-cciwmain-contact_us_done"),

    # Site content
    url(r'^$', sitecontent_views.home, name="cciw-cciwmain-sitecontent_home"),
    # Fallback -- allows any other URL to be defined as arbitary pages.
    # htmlchunk.find will throw a 404 for any URL not defined.
    url(r'^(?:.*)/$|^$', sitecontent_views.find, name="cciw-cciwmain-sitecontent_find"),
]

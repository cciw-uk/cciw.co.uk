import django.contrib.auth.views
import django.contrib.staticfiles.views
import django.views.static
from decorator_include import decorator_include
from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path, register_converter

import cciw.cciwmain.views.debug
import cciw.officers.views
from cciw.bookings.decorators import check_booking_decorator

from . import converters

handler404 = "cciw.cciwmain.views.handler404"

register_converter(converters.FourDigitYearConverter, "yyyy")
register_converter(converters.TwoDigitMonthConverter, "mm")
register_converter(converters.CampIdConverter, "campid")
register_converter(converters.CampIdListConverter, "campidlist")
register_converter(converters.OptInt, "optint")


urlpatterns = [
    path("health-check/", lambda request: HttpResponse(b"OK")),
    # Debug:
    path("debug/", cciw.cciwmain.views.debug.debug),
    path("task-queue-debug/", cciw.cciwmain.views.debug.task_queue_debug, name="task_queue_debug"),
    # Plug in the password reset views (before 'admin')
    path("admin/password_reset/", cciw.officers.views.cciw_password_reset, name="admin_password_reset"),
    path(
        "admin/password_reset/done/",
        django.contrib.auth.views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        django.contrib.auth.views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("reset/done/", django.contrib.auth.views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
    # Other 3rd party views
    path("captcha/", include("captcha.urls")),
    path("admin/", admin.site.urls),
    # Our normal views
    path("booking/", decorator_include([check_booking_decorator], "cciw.bookings.urls")),
    path("officers/", include("cciw.officers.urls")),
    path("notifications/", include("django_nyt.urls")),
    path("wiki/", include("wiki.urls")),
    path("paypal/ipn/", include("paypal.standard.ipn.urls")),
    path("mail/", include("cciw.mail.urls")),
    path("contact/", include("cciw.contact_us.urls")),
    path("documents/", include("cciw.documents.urls")),
    path("visitors/", include("cciw.visitors.urls")),
]

if settings.DEVBOX:
    import debug_toolbar
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += [
        path("usermedia/<path:path>", django.views.static.serve, {"document_root": settings.MEDIA_ROOT}),
    ]

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += [path("django_functest/", include("django_functest.urls"))]

    if settings.DEBUG and "debug_toolbar" in settings.INSTALLED_APPS:
        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns

urlpatterns = urlpatterns + [path("", include("cciw.cciwmain.urls"))]

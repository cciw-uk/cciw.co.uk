from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name="cciw-officers-index"),
    url(r'^applications/$', views.applications, name="cciw-officers-applications"),
    url(r'^view-application/$', views.view_application, name="cciw-officers-view_application"),
    url(r'^correct-email/$', views.correct_email, name="cciw-officers-correct_email"),
    url(r'^correct-application/$', views.correct_application, name="cciw-officers-correct_application"),
    url(r'^leaders/$', views.leaders_index, name="cciw-officers-leaders_index"),
    url(r'^leaders/applications/(?P<year>\d{4})-(?P<slug>[^/]+)/$', views.manage_applications, name="cciw-officers-manage_applications"),
    url(r'^leaders/references/(?P<year>\d{4})-(?P<slug>[^/]+)/$', views.manage_references, name="cciw-officers-manage_references"),
    url(r'^leaders/officer-list/(?P<year>\d{4})-(?P<slug>[^/]+)/$', views.officer_list, name="cciw-officers-officer_list"),
    url(r'^leaders/officer/(?P<officer_id>\d+)/$', views.officer_history, name="cciw-officers-officer_history"),
    url(r'^leaders/export-officer-data/(?P<year>\d{4})-(?P<slug>[^/]+)/$', views.export_officer_data, name="cciw-officers-export_officer_data"),
    url(r'^leaders/export-camper-data/(?P<year>\d{4})-(?P<slug>[^/]+)/$', views.export_camper_data, name="cciw-officers-export_camper_data"),
    url(r'^leaders/export-camper-data/(?P<year>\d{4})/$', views.export_camper_data_for_year, name="cciw-officers-export_camper_data_for_year"),
    url(r'^leaders/export-sharable-transport-details/(?P<year>\d{4})-(?P<slug>[^/]+)/$', views.export_sharable_transport_details, name="cciw-officers-export_sharable_transport_details"),
    url(r'^leaders/remove-officer/(?P<year>\d{4})-(?P<slug>[^/]+)/$', views.remove_officer, name="cciw-officers-remove_officer"),
    url(r'^leaders/add-officers/(?P<year>\d{4})-(?P<slug>[^/]+)/$', views.add_officers, name="cciw-officers-add_officers"),
    url(r'^leaders/update-officer/$', views.update_officer, name="cciw-officers-update_officer"),
    url(r'^leaders/resend-email/$', views.resend_email, name="cciw-officers-resend_email"),
    url(r'^leaders/request-reference/(?P<year>\d{4})-(?P<slug>[^/]+)/$', views.request_reference, name="cciw-officers-request_reference"),
    url(r'^leaders/nag-by-officer/(?P<year>\d{4})-(?P<slug>[^/]+)/$', views.nag_by_officer, name="cciw-officers-nag_by_officer"),
    url(r'^leaders/reference/(?P<reference_id>\d+)/$', views.view_reference, name="cciw-officers-view_reference"),
    url(r'^leaders/crbs/(?P<year>\d{4})/', views.manage_crbs, name="cciw-officers-manage_crbs"),
    url(r'^leaders/mark-crb-sent/', views.mark_crb_sent, name="cciw-officers-mark_crb_sent"),
    url(r'^leaders/undo-mark-crb-sent/', views.undo_mark_crb_sent, name="cciw-officers-undo_mark_crb_sent"),
    url(r'^leaders/crb-consent-problem/', views.crb_consent_problem, name="cciw-officers-crb_consent_problem"),
    url(r'^leaders/officer-stats/(?P<year>\d{4})/$', views.officer_stats, name="cciw-officers-officer_stats"),
    url(r'^leaders/officer-stats-download/(?P<year>\d{4})/$', views.officer_stats_download, name="cciw-officers-officer_stats_download"),
    url(r'^leaders/officer-stats-trend/(?P<start_year>\d{4})-(?P<end_year>\d{4})/$', views.officer_stats_trend, name="cciw-officers-officer_stats_trend"),
    url(r'^leaders/officer-stats-trend-download/(?P<start_year>\d{4})-(?P<end_year>\d{4})/$', views.officer_stats_trend_download, name="cciw-officers-officer_stats_trend_download"),
    url(r'^ref/(?P<referee_id>\d+)-(?P<prev_ref_id>\d*)-(?P<hash>.*)/$', views.create_reference_form, name="cciw-officers-create_reference_form"),
    url(r'^ref/thanks/$', views.create_reference_thanks, name="cciw-officers-create_reference_thanks"),
    url(r'^add-officer/$', views.create_officer, name="cciw-officers-create_officer"),
    url(r'^files/(.*)$', views.officer_files, name="cciw-officers-officer_files"),
    url(r'^info/$', views.officer_info, name="cciw-officers-info"),
    url(r'^bookings/reports/(?P<year>\d{4})/$', views.booking_secretary_reports, name="cciw-officers-booking_secretary_reports"),
    url(r'^bookings/export-payments/$', views.export_payment_data, name="cciw-officers-export_payment_data"),

    # Bookings progress
    url(r'^bookings/booking-progress-stats/(?P<start_year>\d{4})-(?P<end_year>\d{4})/$', views.booking_progress_stats, name="cciw-officers-booking_progress_stats"),
    url(r'^bookings/booking-progress-stats/(?P<camps>\d{4}-[^/]+(,\d{4}-[^/]+)*)/$', views.booking_progress_stats, name="cciw-officers-booking_progress_stats_custom"),
    url(r'^bookings/booking-progress-stats-download/(?P<start_year>\d{4})-(?P<end_year>\d{4})/$', views.booking_progress_stats_download, name="cciw-officers-booking_progress_stats_download"),
    url(r'^bookings/booking-progress-stats-download/(?P<camps>\d{4}-[^/]+(,\d{4}-[^/]+)*)/$', views.booking_progress_stats_download, name="cciw-officers-booking_progress_stats_custom_download"),

    # Bookings summary
    url(r'^bookings/booking-summary-stats/(?P<start_year>\d{4})-(?P<end_year>\d{4})/$', views.booking_summary_stats, name="cciw-officers-booking_summary_stats"),
    url(r'^bookings/booking-summary-stats-download/(?P<start_year>\d{4})-(?P<end_year>\d{4})/$', views.booking_summary_stats_download, name="cciw-officers-booking_summary_stats_download"),
    url(r'^bookings/brochure-mailing-list/(?P<year>\d{4})/$', views.brochure_mailing_list, name="cciw-officers-brochure_mailing_list"),

    # Bookings ages
    url(r'^bookings/booking-ages-stats/(?P<start_year>\d{4})-(?P<end_year>\d{4})/$', views.booking_ages_stats, name="cciw-officers-booking_ages_stats"),
    url(r'^bookings/booking-ages-stats/(?P<camps>\d{4}-[^/]+(,\d{4}-[^/]+)*)/$', views.booking_ages_stats, name="cciw-officers-booking_ages_stats_custom"),
    url(r'^bookings/booking-ages-stats/(?P<single_year>\d{4})/$', views.booking_ages_stats, name="cciw-officers-booking_ages_stats_single_year"),
    url(r'^bookings/booking-ages-stats-download/(?P<start_year>\d{4})-(?P<end_year>\d{4})/$', views.booking_ages_stats_download, name="cciw-officers-booking_ages_stats_download"),
    url(r'^bookings/booking-ages-stats-download/(?P<camps>\d{4}-[^/]+(,\d{4}-[^/]+)*)/$', views.booking_ages_stats_download, name="cciw-officers-booking_ages_stats_custom_download"),

    # Autocomplete
    url(r'^officer-autocomplete/$',
        views.UserAutocomplete.as_view(), name='officer-autocomplete'),

]

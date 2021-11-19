from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="cciw-officers-index"),
    # Application forms
    path("applications/", views.applications, name="cciw-officers-applications"),
    path("get-application/", views.get_application, name="cciw-officers-get_application"),
    path("view-application/", views.view_application_redirect, name="cciw-officers-view_application_redirect"),
    path("view-application/<int:application_id>/", views.view_application, name="cciw-officers-view_application"),
    path("correct-email/", views.correct_email, name="cciw-officers-correct_email"),
    path("correct-application/", views.correct_application, name="cciw-officers-correct_application"),
    # Leaders pages
    path("leaders/", views.leaders_index, name="cciw-officers-leaders_index"),
    path("leaders/applications/<campid:camp_id>/", views.manage_applications, name="cciw-officers-manage_applications"),
    path("leaders/references/<campid:camp_id>/", views.manage_references, name="cciw-officers-manage_references"),
    path("leaders/officer-list/<campid:camp_id>/", views.officer_list, name="cciw-officers-officer_list"),
    path("leaders/officer/<int:officer_id>/", views.officer_history, name="cciw-officers-officer_history"),
    path("add-officer/", views.create_officer, name="cciw-officers-create_officer"),
    path(
        "leaders/export-officer-data/<campid:camp_id>/",
        views.export_officer_data,
        name="cciw-officers-export_officer_data",
    ),
    path(
        "leaders/export-camper-data/<campid:camp_id>/",
        views.export_camper_data,
        name="cciw-officers-export_camper_data",
    ),
    path(
        "leaders/export-camper-data/<yyyy:year>/",
        views.export_camper_data_for_year,
        name="cciw-officers-export_camper_data_for_year",
    ),
    path(
        "leaders/export-sharable-transport-details/<campid:camp_id>/",
        views.export_sharable_transport_details,
        name="cciw-officers-export_sharable_transport_details",
    ),
    path("leaders/remove-officer/<campid:camp_id>/", views.remove_officer, name="cciw-officers-remove_officer"),
    path("leaders/add-officers/<campid:camp_id>/", views.add_officers, name="cciw-officers-add_officers"),
    path("leaders/update-officer/", views.update_officer, name="cciw-officers-update_officer"),
    path("leaders/resend-email/", views.resend_email, name="cciw-officers-resend_email"),
    path(
        "leaders/request-reference/<campid:camp_id>/", views.request_reference, name="cciw-officers-request_reference"
    ),
    path("leaders/nag-by-officer/<campid:camp_id>/", views.nag_by_officer, name="cciw-officers-nag_by_officer"),
    path("leaders/reference/<int:reference_id>/", views.view_reference, name="cciw-officers-view_reference"),
    # DBS
    path("leaders/dbss/<yyyy:year>/", views.manage_dbss, name="cciw-officers-manage_dbss"),
    path("leaders/mark-dbs-sent/", views.mark_dbs_sent, name="cciw-officers-mark_dbs_sent"),
    path("leaders/undo-mark-dbs-sent/", views.undo_mark_dbs_sent, name="cciw-officers-undo_mark_dbs_sent"),
    path(
        "leaders/dbs-consent-alert-leaders/<int:application_id>/",
        views.dbs_consent_alert_leaders,
        name="cciw-officers-dbs_consent_alert_leaders",
    ),
    path(
        "leaders/request-dbs-form-action/<int:application_id>/",
        views.request_dbs_form_action,
        name="cciw-officers-request_dbs_form_action",
    ),
    path("leaders/dbs-checked-online/", views.dbs_checked_online, name="cciw-officers-dbs_checked_online"),
    # Officer stats
    path("leaders/officer-stats/<yyyy:year>/", views.officer_stats, name="cciw-officers-officer_stats"),
    path(
        "leaders/officer-stats-download/<yyyy:year>/",
        views.officer_stats_download,
        name="cciw-officers-officer_stats_download",
    ),
    path(
        "leaders/officer-stats-trend/<yyyy:start_year>-<yyyy:end_year>/",
        views.officer_stats_trend,
        name="cciw-officers-officer_stats_trend",
    ),
    path(
        "leaders/officer-stats-trend-download/<yyyy:start_year>-<yyyy:end_year>/",
        views.officer_stats_trend_download,
        name="cciw-officers-officer_stats_trend_download",
    ),
    # References
    path(
        "ref/<int:referee_id>-<optstr:prev_ref_id>-<hash>/",
        views.create_reference,
        name="cciw-officers-create_reference",
    ),
    path("ref/thanks/", views.create_reference_thanks, name="cciw-officers-create_reference_thanks"),
    # Officer other
    path("files/<path:path>", views.officer_files, name="cciw-officers-officer_files"),
    path("info/", views.officer_info, name="cciw-officers-info"),
    # Booking secretary functions:
    path(
        "bookings/reports/<yyyy:year>/", views.booking_secretary_reports, name="cciw-officers-booking_secretary_reports"
    ),
    path("bookings/export-payments/", views.export_payment_data, name="cciw-officers-export_payment_data"),
    path("bookings/booking-places-json/", views.booking_places_json, name="cciw-officers-booking_places_json"),
    path("bookings/booking-account-json/", views.booking_account_json, name="cciw-officers-booking_account_json"),
    path("bookings/booking-problems-json/", views.booking_problems_json, name="cciw-officers-booking_problems_json"),
    path(
        "bookings/expected-amount-json/",
        views.get_booking_expected_amount_due,
        name="cciw-officers-get_booking_expected_amount_due",
    ),
    # Bookings progress
    path(
        "bookings/booking-progress-stats/<yyyy:start_year>-<yyyy:end_year>/",
        views.booking_progress_stats,
        name="cciw-officers-booking_progress_stats",
    ),
    path(
        "bookings/booking-progress-stats/<campidlist:camp_ids>/",
        views.booking_progress_stats,
        name="cciw-officers-booking_progress_stats_custom",
    ),
    path(
        "bookings/booking-progress-stats-download/<yyyy:start_year>-<yyyy:end_year>/",
        views.booking_progress_stats_download,
        name="cciw-officers-booking_progress_stats_download",
    ),
    path(
        "bookings/booking-progress-stats-download/<campidlist:camp_ids>/",
        views.booking_progress_stats_download,
        name="cciw-officers-booking_progress_stats_custom_download",
    ),
    # Bookings summary
    path(
        "bookings/booking-summary-stats/<yyyy:start_year>-<yyyy:end_year>/",
        views.booking_summary_stats,
        name="cciw-officers-booking_summary_stats",
    ),
    path(
        "bookings/booking-summary-stats-download/<yyyy:start_year>-<yyyy:end_year>/",
        views.booking_summary_stats_download,
        name="cciw-officers-booking_summary_stats_download",
    ),
    path(
        "bookings/brochure-mailing-list/<yyyy:year>/",
        views.brochure_mailing_list,
        name="cciw-officers-brochure_mailing_list",
    ),
    # Bookings ages
    path(
        "bookings/booking-ages-stats/<yyyy:start_year>-<yyyy:end_year>/",
        views.booking_ages_stats,
        name="cciw-officers-booking_ages_stats",
    ),
    path(
        "bookings/booking-ages-stats/<campidlist:camp_ids>/",
        views.booking_ages_stats,
        name="cciw-officers-booking_ages_stats_custom",
    ),
    path(
        "bookings/booking-ages-stats/<yyyy:single_year>/",
        views.booking_ages_stats,
        name="cciw-officers-booking_ages_stats_single_year",
    ),
    path(
        "bookings/booking-ages-stats-download/<yyyy:start_year>-<yyyy:end_year>/",
        views.booking_ages_stats_download,
        name="cciw-officers-booking_ages_stats_download",
    ),
    path(
        "bookings/booking-ages-stats-download/<campidlist:camp_ids>/",
        views.booking_ages_stats_download,
        name="cciw-officers-booking_ages_stats_custom_download",
    ),
]

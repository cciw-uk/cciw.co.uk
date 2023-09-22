"""
View functions for officers.

This set of modules is organised roughly by role, although this is difficult to
do exactly.

"""
# ruff: noqa: F401

from django.contrib.auth.views import PasswordResetView

from ..forms import (
    CciwPasswordResetForm,
)
from .applications import (
    applications,
    correct_application,
    correct_email,
    get_application,
    view_application,
    view_application_redirect,
)
from .booking_secretary import (
    booking_problems_json,
    booking_secretary_reports,
    booking_summary_stats,
    booking_summary_stats_download,
    brochure_mailing_list,
    export_camper_data_for_year,
    export_payment_data,
    get_booking_expected_amount_due,
    place_availability_json,
)
from .dbs import (
    dbs_checked_online,
    dbs_consent_alert_leaders,
    dbs_register_received,
    manage_dbss,
    mark_dbs_sent,
    request_dbs_form_action,
)
from .general import officer_files, officer_info
from .leaders import (
    booking_ages_stats,
    booking_ages_stats_download,
    booking_progress_stats,
    booking_progress_stats_download,
    correct_referee_details,
    create_officer,
    export_camper_data,
    export_officer_data,
    export_sharable_transport_details,
    fill_in_reference_manually,
    manage_applications,
    manage_references,
    nag_by_officer,
    officer_application_status,
    officer_history,
    officer_list,
    officer_stats,
    officer_stats_download,
    officer_stats_trend,
    officer_stats_trend_download,
    request_reference,
    resend_email,
    update_officer,
    view_reference,
)
from .menus import index, leaders_index
from .referees import create_reference, create_reference_thanks
from .webmaster import data_erasure_request_execute, data_erasure_request_plan, data_erasure_request_start

cciw_password_reset = PasswordResetView.as_view(form_class=CciwPasswordResetForm)

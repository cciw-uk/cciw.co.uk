from cciw.utils.views import user_passes_test_improved


def any_passes(*funcs):
    def func(*args, **kwargs):
        for f in funcs:
            if f(*args, **kwargs):
                return True
        return False

    return func


camp_admin_required = user_passes_test_improved(lambda u: u.is_camp_admin)
dbs_officer_required = user_passes_test_improved(lambda u: u.is_dbs_officer)
dbs_officer_or_camp_admin_required = user_passes_test_improved(lambda u: u.is_dbs_officer or u.is_camp_admin)
booking_secretary_required = user_passes_test_improved(lambda u: u.is_booking_secretary)
booking_secretary_or_treasurer_required = user_passes_test_improved(
    any_passes(lambda u: u.is_booking_secretary, lambda u: u.is_treasurer)
)
cciw_secretary_required = user_passes_test_improved(lambda u: u.is_cciw_secretary)
cciw_secretary_or_booking_secretary_required = user_passes_test_improved(
    any_passes(lambda u: u.is_booking_secretary, lambda u: u.is_cciw_secretary)
)
secretary_or_committee_required = user_passes_test_improved(
    any_passes(lambda u: u.is_booking_secretary, lambda u: u.is_cciw_secretary, lambda u: u.is_committee_member)
)
potential_camp_officer_required = user_passes_test_improved(lambda u: u.is_potential_camp_officer)
webmaster_required = user_passes_test_improved(lambda u: u.is_superuser)

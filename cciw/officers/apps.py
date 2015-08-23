from django.apps import AppConfig


class OfficersConfig(AppConfig):

    def ready(self):
        from django.contrib.auth import get_user_model
        from django.utils.functional import cached_property
        from cciw.officers.models import camps_as_admin_or_leader
        from cciw.cciwmain.common import get_thisyear

        User = get_user_model()
        User.camps_as_admin_or_leader = cached_property(camps_as_admin_or_leader)
        User.current_camps_as_admin_or_leader = cached_property(lambda user: [c for c in user.camps_as_admin_or_leader
                                                                              if c.year == get_thisyear()])

    name = 'cciw.officers'

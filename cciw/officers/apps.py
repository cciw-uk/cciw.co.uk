from django.apps import AppConfig

class OfficersConfig(AppConfig):

    def ready(self):
        from django.contrib.auth import get_user_model
        from django.utils.functional import cached_property
        from cciw.officers.models import camps_as_admin_or_leader

        User = get_user_model()
        User.camps_as_admin_or_leader = cached_property(camps_as_admin_or_leader)

    name = 'cciw.officers'

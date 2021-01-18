from django.contrib.admin.apps import AdminConfig


class CciwAdminConfig(AdminConfig):
    default_site = 'cciw.admin.CciwAdminSite'

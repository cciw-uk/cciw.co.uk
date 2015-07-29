from functools import wraps

from cciw.cciwmain.models import Site, Person, Camp, Role
from django.contrib import admin


def rename_app_list(func):
    m = {'Cciwmain': 'Camp info',
         'Sitecontent': 'Site content',
         'Sites': 'Web sites'
         }

    @wraps(func)
    def _wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        app_list = response.context_data.get('app_list')
        if app_list is not None:
            for a in app_list:
                name = a['name']
                a['name'] = m.get(name, name)
        title = response.context_data.get('title')
        if title is not None:
            app_label = title.split(' ')[0]
            if app_label in m:
                response.context_data['title'] = "%s administration" % m[app_label]
        return response
    return _wrapper

admin.site.index = rename_app_list(admin.site.index)
admin.site.app_index = rename_app_list(admin.site.app_index)


class SiteAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('short_name', 'long_name', 'info')}),
    )


class PersonAdmin(admin.ModelAdmin):
    filter_horizontal = ('users',)
    search_fields = ['name']
    list_display = ['name', 'info']


class CampAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Public info',
         {'fields': ('year', 'number', 'minimum_age', 'maximum_age', 'start_date', 'end_date',
                     'leaders', 'chaplain', 'site', 'previous_camp')
          }
         ),
        ('Booking constraints',
         {'fields': ('max_campers', 'max_male_campers', 'max_female_campers',
                     'last_booking_date',
                     'south_wales_transport_available')
          }
         ),
        ('Applications and references',
         {'fields': ['admins'],
          'description': '<div>Options for managing applications. Officer lists are managed <a href="/officers/leaders/">elsewhere</a>, not here.</div>',
          }
         ),
    )
    ordering = ('-year', 'number')

    def leaders(camp):
        return camp.leaders_formatted

    def chaplain(camp):
        return camp.chaplain
    chaplain.admin_order_field = 'chaplain__name'
    list_display = ('year', 'number', leaders, chaplain, 'age', 'site', 'start_date')
    list_display_links = ('number', leaders)
    del leaders, chaplain
    list_filter = ('site',)
    filter_horizontal = ('leaders', 'admins')
    date_hierarchy = 'start_date'

    def get_queryset(self, request):
        return super(CampAdmin, self).get_queryset(request).select_related('site', 'chaplain')

admin.site.register(Site, SiteAdmin)
admin.site.register(Person, PersonAdmin)
admin.site.register(Camp, CampAdmin)
admin.site.register(Role)

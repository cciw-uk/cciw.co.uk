from functools import wraps

from django.contrib import admin
from django.utils.html import format_html

from cciw.cciwmain.models import Camp, CampName, Person, Site


def rename_app_list(func):
    m = {"Cciwmain": "Camp info", "Sitecontent": "Site content", "Sites": "Web sites"}

    @wraps(func)
    def _wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        app_list = response.context_data.get("app_list")
        if app_list is not None:
            for a in app_list:
                name = a["name"]
                a["name"] = m.get(name, name)
        title = response.context_data.get("title")
        if title is not None:
            app_label = title.split(" ")[0]
            if app_label in m:
                response.context_data["title"] = f"{m[app_label]} administration"
        return response

    return _wrapper


admin.site.index = rename_app_list(admin.site.index)
admin.site.app_index = rename_app_list(admin.site.app_index)


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    fieldsets = ((None, {"fields": ("short_name", "long_name", "info")}),)


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    filter_horizontal = ("users",)
    search_fields = ["name"]
    list_display = ["name", "info"]


@admin.register(CampName)
class CampNameAdmin(admin.ModelAdmin):
    def color_swab(camp_name):
        return format_html(
            '<span style="width:100px; height:15px; display: inline-block; background-color: {0}"></span>',
            camp_name.color,
        )

    color_swab.short_description = "Colour"
    list_display = ["name", "slug", color_swab]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(Camp)
class CampAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "Public info",
            {
                "fields": (
                    "year",
                    "camp_name",
                    "old_name",
                    "minimum_age",
                    "maximum_age",
                    "start_date",
                    "end_date",
                    "leaders",
                    "chaplain",
                    "site",
                )
            },
        ),
        (
            "Booking constraints",
            {
                "description": "Changes to booking limits need to be coordinated with the booking secretary.",
                "fields": ("max_campers", "max_male_campers", "max_female_campers", "last_booking_date"),
            },
        ),
        (
            "Applications and references",
            {
                "fields": ["admins"],
                "description": '<div>Options for managing applications. Officer lists are managed <a href="/officers/leaders/">elsewhere</a>, not here.</div>',
            },
        ),
        ("Extra", {"fields": ("special_info_html",)}),
    )
    ordering = ("-year", "start_date")
    readonly_fields = ["old_name"]

    def leaders(camp):
        return camp.leaders_formatted

    def chaplain(camp):
        return camp.chaplain

    chaplain.admin_order_field = "chaplain__name"
    list_display = [
        "year",
        "camp_name",
        leaders,
        chaplain,
        "age",
        "site",
        "start_date",
        "old_name",
    ]

    list_display_links = ("camp_name", leaders)
    del leaders, chaplain
    list_filter = ["camp_name", "site"]
    filter_horizontal = ("leaders", "admins")
    date_hierarchy = "start_date"

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("site", "chaplain")
        if request.user.has_perm("cciwmain.change_camp"):
            return qs
        else:
            return qs.filter(id__in=[c.id for c in request.user.viewable_camps])

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        # Some users (Camp leaders) have permissions to edit their own camp for
        # some purposes, which is enabled via custom logic in
        # `has_change_permission` below.

        # But giving them unrestricted editing powers makes things difficult
        # (particularly if the booking secretary is managing a waiting list for
        # a camp). So we limit users who don't have full "cciwmain.change_camp"
        # permissions
        if not request.user.has_perm("cciwmain.change_camp"):
            readonly_fields += ["max_male_campers", "max_female_campers", "max_campers", "last_booking_date"]
        return readonly_fields

    def has_change_permission(self, request, obj=None):
        if obj is None:
            if request.user.can_edit_some_camps:
                return True
        else:
            if request.user.can_edit_camp(obj):
                return True
        return super().has_change_permission(request, obj=obj)

    def has_view_permission(self, request, obj=None):
        if obj is None:
            if request.user.can_edit_some_camps:
                return True
        else:
            if request.user.can_view_camp(obj):
                return True
        return super().has_view_permission(request, obj=obj)

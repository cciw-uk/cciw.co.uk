from django import template

register = template.Library()


# Used to override part of normal 'submit row' for application forms
# UGLY HACK!
class FixPermissions(template.Node):
    def render(self, context):
        for d in context.dicts:
            if "has_change_permission" in d:
                # We don't want 'Save and add another' to appear
                d["has_add_permission"] = False

        return ""


def fix_permissions(parser, token):
    return FixPermissions()


register.tag("fix_permissions", fix_permissions)

from django import template

register = template.Library()

# Overrides normal 'submit row'
def application_submit_row(context):
    opts = context['opts']
    change = context['change']
    is_popup = context['is_popup']
    return {
        'onclick_attrib': (opts.get_ordered_objects() and change
                            and 'onclick="submitOrderForm();"' or ''),
        'show_delete_link': (not is_popup and context['has_delete_permission']
                              and (change or context['show_delete'])),
        'show_save_as_new': False, # CHANGED - never want this
        'show_save_and_add_another': False, # CHANGED - never want this
        'show_save_and_continue': not is_popup, # CHANGED (allow button without change_permission)
        'show_save': True
    }

application_submit_row = register.inclusion_tag('admin/submit_line', takes_context=True)(application_submit_row)

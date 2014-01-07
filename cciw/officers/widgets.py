from django.contrib import admin


class ExplicitBooleanFieldSelect(admin.widgets.AdminRadioSelect):
    """
    A Radio select widget intended to be used with NullBooleanField.
    """
    def __init__(self, attrs=None):
        if attrs is None:
            attrs = {}
        attrs.update({'class':'radiolist inline'})
        choices = ((u'2', 'Yes'), (u'3', 'No'))
        super(ExplicitBooleanFieldSelect, self).__init__(attrs, choices)

    def render(self, name, value, attrs=None, choices=()):
        try:
            value = {True: u'2', False: u'3', u'2': u'2', u'3': u'3'}[value]
        except KeyError:
            value = u'1'
        return super(ExplicitBooleanFieldSelect, self).render(name, value, attrs, choices)

    def value_from_datadict(self, data, files, name):
        value = data.get(name, None)
        return {u'2': True, u'3': False, True: True, False: False}.get(value, None)

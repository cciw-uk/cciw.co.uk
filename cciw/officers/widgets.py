from django.contrib import admin


class ExplicitBooleanFieldSelect(admin.widgets.AdminRadioSelect):
    """
    A Radio select widget intended to be used with a nullable BooleanField.
    """
    def __init__(self, attrs=None):
        if attrs is None:
            attrs = {}
        attrs.update({'class': 'radiolist inline'})
        choices = [
            ('2', 'Yes'),
            ('3', 'No'),
        ]
        super(ExplicitBooleanFieldSelect, self).__init__(attrs, choices)

    def render(self, name, value, attrs=None, renderer=None):
        try:
            value = {True: '2', False: '3', '2': '2', '3': '3'}[value]
        except KeyError:
            value = '1'
        return super(ExplicitBooleanFieldSelect, self).render(name, value, attrs, renderer=renderer)

    def value_from_datadict(self, data, files, name):
        value = data.get(name)
        return {
            '2': True,
            True: True,
            'True': True,
            '3': False,
            'False': False,
            False: False,
        }.get(value)

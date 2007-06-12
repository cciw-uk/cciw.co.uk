from django import template
from django.template import loader

def application_to_text(app):
    t = loader.get_template('cciw/officers/application_email.txt');
    return t.render(template.Context({'app': app}))

def application_to_rtf(app):
    raise NotImplementedError()

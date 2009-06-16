from django import template
from django.template import loader

def application_to_text(app):
    t = loader.get_template('cciw/officers/application_email.txt');
    return t.render(template.Context({'app': app}))

def application_to_rtf(app):
    t = loader.get_template('cciw/officers/application.rtf');
    return t.render(template.Context({'app': app}))

def application_rtf_filename(app):
    return _application_filename_stem(app) + ".rtf"

def application_txt_filename(app):
    return _application_filename_stem(app) + ".txt"

def _application_filename_stem(app):
    return 'Application_%s_%s' % (app.officer.username, app.camp.year)

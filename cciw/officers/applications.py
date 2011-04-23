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
    if app.date_submitted is None:
        submitted = ''
    else:
        submitted = '_' + app.date_submitted.strftime('%Y-%m-%d')
    return 'Application_%s%s' % (app.officer.username, submitted)

def application_difference(app1, app2):
    from diff_match_patch import diff_match_patch
    differ = diff_match_patch()
    diffs = differ.diff_main(application_to_text(app1),
                             application_to_text(app2))
    differ.diff_cleanupSemantic(diffs)
    html = differ.diff_prettyHtml(diffs)
    # It looks better without the '&para;'
    html = html.replace('&para;', '')

    # Use custom colours etc.
    html = html.replace('background:#E6FFE6;', '')
    html = html.replace('background:#FFE6E6;', '')
    html = html.replace(' STYLE=""', '')

    return """<html>
<style>
body {
    font-family:monospace;
}

ins {
    background: #51FF17;
    text-decoration: none;
    font-weight: bold;
}

del {
   background: #FF6989;
   text-decoration: strike-through;
}
</style>
<body><pre>%s</pre></body></html>""" % html

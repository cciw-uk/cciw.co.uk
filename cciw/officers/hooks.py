# Hooks for various events

from cciw.officers import signals
from django.dispatch import dispatcher
from django.core.mail import send_mail
from django.conf import settings
from django import template
import os

def send_leader_email(application=None):
    if not application.finished:
        return
    
    leaders = application.camp.leaders.all()
    if len(leaders) == 0:
        return
    
    # Collect e-mails to send to
    emails = []
    for leader in leaders:
        # Does the leader have an associated admin login?
        if leader.user is not None:
            user = leader.user
            email = user.email.strip()
            if len(email) > 0:
                name = (user.first_name + " " + user.last_name).strip().replace('"', '')
                if len(name) > 0:
                    email = '"%s" <%s>' % (name, email)
                emails.append(email)
    if len(emails) == 0:
        return
    t = template.Template("""
The following application form has been submitted
via the CCIW website:
    
For camp:         {{ app.camp }}

Personal info
=============
Name:             {{ app.full_name }}
Maiden name:      {{ app.full_maiden_name }}
Date of birth:    {{ app.birth_date }}
Place of birth:   {{ app.birth_place }}
Address:          {{ app.address_firstline }}
                  {{ app.address_town }}
                  {{ app.address_county }}
                  {{ app.address_postcode }}
                  {{ app.address_country }}
Tel:              {{ app.address_tel }}
Mobile:           {{ app.address_mobile }}
E-mail:           {{ app.address_email }}
At this address since: {{ app.address_since }}

{% if app.address2_from or app.address3_from %}
----------------------------------------------------------------------
Previous addresses
==================
{% if app.address2_from %}Previous address 1:
From:             {{ app.address2_from }}
To:               {{ app.address2_to }}
Address:
--------
{{ app.address2_address }}{% endif %}

{% if app.address3_from %}Previous address 2:
From:             {{ app.address3_from }}
To:               {{ app.address3_to }}
Address:
--------
{{ app.address3_address }}{% endif %}{% endif %}
----------------------------------------------------------------------
Statements
==========
Christian experience:
---------------------
{{ app.christian_experience|wordwrap:70 }}

Youth work experience:
----------------------
{{ app.youth_experience|wordwrap:70 }}

Have you ever had an offer to work 
with children/young people declined?    {{ app.youth_work_declined|yesno:"YES,NO,-" }}

Details:
--------
{{ app.youth_work_declined_details|wordwrap:70 }}
----------------------------------------------------------------------
Illnesses
=========
Do you suffer or have you suffered from 
any illness which may directly affect 
your work with children/young people?   {{ app.relevant_illness|yesno:"YES,NO,-" }}

Details:
--------
{{ app.illness_details|wordwrap:70 }}
----------------------------------------------------------------------
Employment history
==================
{% if app.employer1_name %}Employer 1
Name:             {{ app.employer1_name }}
From:             {{ app.employer1_from }}
Til:              {{ app.employer1_to }}
Job description:  {{ app.employer1_job }}
Reason for leaving:
  {{ app.employer1_leaving|wordwrap:70 }}
{% endif %}

{% if app.employer2_name %}Employer 2
Name:             {{ app.employer2_name }}
From:             {{ app.employer2_from }}
Til:              {{ app.employer2_to }}
Job description:  {{ app.employer2_job }}
Reason for leaving:
  {{ app.employer2_leaving|wordwrap:70 }}
{% endif %}
----------------------------------------------------------------------
References
==========
Referee 1:        {{ app.referee1_name }}
Address:
{{ app.referee1_address }}
Tel:              {{ app.referee1_tel }}
Mobile:           {{ app.referee1_mobile }}
E-mail:           {{ app.referee1_email }}

Referee 2:        {{ app.referee2_name }}
Address:
{{ app.referee2_address }}
Tel:              {{ app.referee2_tel }}
Mobile:           {{ app.referee2_mobile }}
E-mail:           {{ app.referee2_email }}
----------------------------------------------------------------------
Declarations
============
Have you ever been charged 
with or convicted of a criminal
offence or are the subject of
criminal proceedings?                   {{ app.crime_declaration|yesno:"YES,NO,-" }}

Details:
--------
{{ app.crime_details|wordwrap:70 }}

Have you ever been involved in court
proceedings concerning a child for 
whom you have parental responsibility?  {{ app.court_declaration|yesno:"YES,NO,-" }}

Details:
--------
{{ app.court_details|wordwrap:70 }}

Has there ever been any cause for 
concern  regarding your conduct with 
children/young people?                  {{ app.concern_declaration|yesno:"YES,NO,-" }}

Details:
--------
{{ app.concern_details|wordwrap:70 }}

To your knowledge have you ever had 
any allegation made against you 
concerning children/young people which 
has been reported to and investigated 
by Social Services and /or the Police?  {{ app.allegation_declaration|yesno:"YES,NO,-" }}

Do you consent to the obtaining of 
a Criminal Records Bureau check 
on yourself?                            {{ app.crb_check_consent|yesno:"YES,NO,-" }}

    """)
    
    
    msg = t.render(template.Context({'app': application}))
    subject = "CCIW application form from %s" % application.full_name
    # debug
    print "sending mail:"
    print subject
    print msg
    
    send_mail(subject, msg, settings.SERVER_EMAIL, emails)

dispatcher.connect(send_leader_email, signal=signals.application_saved)

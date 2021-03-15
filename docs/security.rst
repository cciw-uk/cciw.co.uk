Security and data protection
============================

This document forms part of CCiW's data protection policies, and significant
changes to it must be discussed with the committee. It is kept with the website
source code in order to keep "policy" and "implementation of the policy" as
close together as possible. In many cases it is not possible to understand how
to develop the CCiW website and its features without an understanding of
security and data protection principles, so this forms part of the web developer
documentation.

The CCiW website database stores personal information of various kinds. Because
of this, having a secure site is a very high priority.

Please also note that this repo, including this documentation, is publicly
readable (on VCS hosting and possibly elsewhere). This is good for transparency,
but also means that extra care must be taken not to include sensitive data in
the source code.

A separate document "CCiW website access information" is available outside this
repository. This details services we use for our website, and how we give access
to these services to CCiW staff - please refer to that document also.

Basic security principles
-------------------------

Regarding things more directly touching development of code in this repo, the
following points must be observed:

* Security of the system must not depend on "security by obscurity". This is
  always a bad idea, and in our case we have no obscurity as the source code is
  public.

* All access to the website must be encrypted - using HTTPS for web access,
  and SSH for server access.

* Where possible we should use reputable, open source, reviewed code for
  security related features, rather than "roll our own". In particular we should
  use Django's security features wherever appropriate.

* The webmaster must understand the security risks relevant to developing web
  sites, such as those listed in the `OWASP Top Ten
  <https://owasp.org/www-project-top-ten/>`_, and know how to design systems
  securely with these risks in mind.

* We prefer a simple architecture that is easy to understand and therefore easy
  to secure - more below.

* It is the webmaster's responsibility to ensure that all software in the CCiW
  website and necessary development tools are kept up to date with relevant
  security patches.

Data protection and privacy
---------------------------

The webmasters are responsible for understanding relevant data protection and
privacy laws, including GDPR, and implementing processes that abide by relevant
laws and fit CCiW's way of working. Processes should be designed and changed
with agreement from the CCiW trustees, and in communication with the other
relevant volunteers, especially the DBS Officers and the Booking Secretary.

For more information on the legal issues, please see:

* The ICO's `Guide to Data Protection
  <https://ico.org.uk/for-organisations/guide-to-data-protection/>`_
* `The GDPR legislaton <https://gdpr.eu/tag/gdpr/>`_
* The 'Decision and actions' document from February 2021 which provides
  a lot of the thinking behind the policies implemented here.
* If you have further questions consult with the CCiW committee.

If you are thinking of making significant changes or additions to CCiW
functionality, please see the helpful ICO document `Data Protection by design
and default
<https://ico.org.uk/for-organisations/guide-to-data-protection/guide-to-the-general-data-protection-regulation-gdpr/accountability-and-governance/data-protection-by-design-and-default/>`_.

The following sections form part of our current approach to data protection. See
also the relevant parts of the CCiW handbook.

Storage of sensitive information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* The source code in this project should not contain any information that is
  private to CCiW and specific to the deployment of this project. This includes
  all passwords and API keys. These should instead be stored in the file
  ``config/secrets.json``, and, if more than one developer is working on the
  project, synchronised via secure channels as agreed by other developers.

* The source code must not contain personal information - for example the email
  addresses or names of people to be emailed in different circumstances.
  Instead, these should be stored:

  * In the database, usually making these values editable via the Django admin
    by people with appropriate permission levels.

  * In ``secrets.json`` as a last resort.

* Camper data and officer data that are supplied as part of booking and
  application forms are stored in the database.

* Retention of all personal data must be done in accord with the relevant data
  protection laws. This is automated by ``cciw/data_retention.py``, using the
  official data retention policy that is part of the source code. See also
  backup policy (below).

Access to information
~~~~~~~~~~~~~~~~~~~~~

* Access to all officer functionality must be controlled on a "need to know"
  basis. The primary places where these are controlled are:

  * permission related methods on the ``User`` model in `</cciw/accounts/models.py>`_
  * permission decorators on views in `</cciw/officers/views.py>`_
  * definitions of group permissions in `</config/static_roles.yaml>`_
  * other functions in `</cciw/auth.py>`_

* As much as possible, privileged access roles should be determined dynamically,
  rather than by manual configuration of permission groups that have to be kept
  up to date. For example, by linking the ``User``, ``Camp`` and ``Person``
  models, we can dynamically determine whether a ``User`` account corresponds to
  a ``Person`` who is a leader of a current camp, rather than by having to
  maintain a group “leaders of current camps”.

  (Due to ``Person`` records sometimes being a married couple, the relationship
  with ``User`` is not a one-to-one, but many-to-many).

* If dynamic roles are not possible, we can create static roles for additional
  permissions, which is managed by `</config/static_roles.yaml>`_.

* Privileged access must be limited in time - for example, being a leader one
  year does not mean a person should have higher access in subsequent years.

* Webmasters have access to all information in the database, which is
  appropriate given the small size of our organisation and the difficulty
  of designing an architecture in which the webmasters could deploy code,
  access backups etc. but not access all the data itself.

  Note, however, that the webmasters must abide by the same "need to know"
  principle when viewing data, and it is illegal to use any data except for the
  purposes that CCiW have agreed, as laid out in `GDPR Article 32 paragraph 4
  <https://gdpr-info.eu/art-32-gdpr/>`_.

Distribution of information
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Note that:

* All CCiW "staff" are unpaid volunteers, and we have no CCiW office.

* We have no “CCiW owned” machines - volunteers use their own machines and
  devices to access data.

* CCiW volunteers will all use their own personal email addresses for CCiW
  business. This is a deliberate choice for various reasons, including the fact
  that it can be hard to stop 3rd parties from using our personal email
  addresses, since we are often known personally by many people who want to
  contact us regarding CCiW business (such as campers).

We therefore design our processes with these things in mind:

* The machine that runs the CCiW website and database is by far the easiest
  machine to secure. The easiest way to ensure compliance is to centralise the
  processing of sensitive information to that machine. For this reason, the
  webmasters have special responsibility regarding understanding and
  implementing data protection processes.

* We do not provide means to download sensitive data unless necessary, and
  should design processes to minimise the need for any sensitive data to be held
  on volunteer machines.

* The website should never email sensitive data, and we do not allow sensitive
  data to be emailed between different volunteers, because it is often too
  difficult to ensure that data held in email accounts is disposed of properly.


Third party services
~~~~~~~~~~~~~~~~~~~~

We should be very careful about integrating 3rd party services. This means:

* avoiding the use of 3rd parties unless necessary
* choosing reliable, proven companies who have appropriate privacy policies
* minimising the data we send to them
* avoiding integration via Javascript that is not under our control, because
  flaws in these can easily open us up to many types of attacks.

See `GDPR Article 28 <https://gdpr-info.eu/art-28-gdpr/>`_ for more information.

Ensuring compliance and training
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In addition to avoiding the need for sensitive data to be found on less secure
systems, we also try to build compliance with data protection laws and training
into our processes themselves:

* Whenever sensitive data is about to be downloaded, we display short,
  digestible information regarding CCiW's policy on its use and disposal.
  **TODO**

* We do **not** attempt to ensure compliance by use of checkboxes that ask
  people if they have read a data protection policy, because we know that
  psychologically people are extremely unlikely to read long documents at the
  point when they are trying to achieve something else.

* Where data is downloaded with the purpose of printing and potential further
  distribution (as is needed for some purposes), we include cover sheets that
  remind users of data protection responsibilities, and remind leaders to
  briefly train other people who will receive the data (such as officers)
  regarding these principles. **TODO**

* After the end of camps, we send reminders to relevant people who have
  downloaded sensitive data, prompting them to delete them. **TODO**


Backups
~~~~~~~

Our production database is backed up by ``backup_s3.py``, using a scheduled
task. These backups have a short expiration date of 30 days, in order to be able
to comply with our data retention policy without having to delete or modify
backups. See also `<services.rst>`_.

We also have whole machine backups from our hosting provider, which also go back
at most 30 days.

It needs to be remembered that backups are a potential security hazard, as they
offer another route to gaining access to our database, and backup processes must
be designed with this in mind.

Data breaches
~~~~~~~~~~~~~

In the case of a data breach (such as our database being hacked,
access being given to the wrong people, or sent to the wrong person), you should:

* attempt to contain the breach if possible - for example, by contacting the
  person to whom the information was wrongly passed on and asking them to erase
  it and not pass it on further, or taking immediate action to secure the website.

* inform the CCiW chairperson, and decide together what further action should be
  taken, including whether to report to the data subjects and ICO. If we do need
  to report to ICO, it has to be done within strict time limits (72 hours), so
  this action needs to be taken promptly.

  See:

  * `ICO on personal data breaches
    <https://ico.org.uk/for-organisations/guide-to-data-protection/guide-to-the-general-data-protection-regulation-gdpr/personal-data-breaches/>`_

  To decide whether to report to the ICO, see `ICO's Report a breach
  <https://ico.org.uk/for-organisations/report-a-breach/>`_

* record the incident in
  https://docs.google.com/document/d/1ZtxOahH7ywNTPd2kuTtScn7OUPA5mloa

Data rights
~~~~~~~~~~~

The GDPR gives data subjects various rights regarding their data, and the CCiW
webmaster is usually the person responsible for providing those facilities, either
by features built into the website functionality, or by more manual processes.

These rights are dealt with `Chapter 3 of the GDPR
<https://gdpr-info.eu/chapter-3/>`_, and it is the responsibility of the
webmaster to understand these laws, including the need to be sure of the
identity of the person asking, the need for timely responses, and the right to
require a fee for processing in some cases (which should be agreed with the CCiW
trustees).

Note that there are also limitations to these data rights, and it is important
that requests are not dealt with in a way that compromises CCiW's obligations in
other areas. Where there are doubts, the trustees should be consulted, and it is
usually best to encode the decisions into tested automated functionality to
reduce human error. This functionality may grow as necessary as more requests
of this nature are dealt with.

**TODO** Details of what we don't provide, to be agreed.


Architecture and encryption
---------------------------

For better security, we prefer to keep things as simple as possible. Since the
application is very small, and can be easily served by a single machine, we have
a single Virtual Private Server which hosts both the database and the web
servers. This allows us to avoid the complexities of things like AWS services or
other systems where there are many policies regarding security that can easily
be misconfigured. It also means we can keep our database locked down to only
accept localhost connections.

For a simple configuration like this, there is little to zero benefit from some
security mechanisms such as "encrypted at rest" databases. (Since the decryption
key has to be on the same machine as the database, if the database machine is
compromised then the key will also be compromised). Since adding these would
only increase complexity, and also the possibility of accidental data loss, we
currently do not encrypt data at rest.

We do use encryption at rest for any 3rd party services that we use e.g.
database backups on Amazon S3. Amazon S3 itself manages the encryption key for
us.

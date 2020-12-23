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

* Architecture - TODO


Data protection and privacy
---------------------------

The web master is responsible for understanding relevant data protection and
privacy laws, including GDPR, and implementing processes that abide by relevant
laws and fit CCiW's way of working.

For more information on these legal issues, please see:

* The ICO's `Guide to Data Protection
  <https://ico.org.uk/for-organisations/guide-to-data-protection/>`_
* `The GDPR legislaton <https://gdpr.eu/tag/gdpr/>`_
* If you have further questions consult with the CCiW committee.

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
  protection laws. This is automated by TODO, using the official data retention
  policy that is part of the source code. See also backup policy (below).

Access to information
~~~~~~~~~~~~~~~~~~~~~

* Access to all officer functionality must be controlled on a "need to know
  basis". The primary places where these are controlled are:

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
  processing of sensitive information to that machine. For this reason, the web
  master has special responsibility regarding understanding and implementing
  data protection processes.

* We do not provide means to download sensitive data unless necessary, and
  should design processes to minimise the need for any sensitive data to be held
  on volunteer machines.

* The website should never email sensitive data, and we do not allow sensitive
  data to be emailed between different members of staff, because it is often too
  difficult to ensure that data held in email accounts is disposed of properly.

Ensuring compliance and training
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In addition to avoiding the need for sensitive data to be found on less secure
systems, we also try to build compliance with data protection laws and training
into our processes themselves:

* Whenever sensitive data is about to be downloaded, we display short,
  digestible information regarding CCiW's policy on its use and disposal.
  ``STATUS:TODO``

* We do **not** attempt to ensure compliance by use of checkboxes that ask
  people if they have read a data protection policy, because we know that
  psychologically people are extremely unlikely to read long documents at the
  point when they are trying to achieve something else.

* Where data is downloaded with the purpose of printing and potential further
  distribution (as is needed for some purposes), we include cover sheets that
  remind users of data protection responsibilities, and remind leaders to
  briefly train other people who will receive the data (such as officers)
  regarding these principles. ``STATUS:TODO``

* After the end of camps, we send reminders to relevant people who have
  downloaded sensitive data, prompting them to delete them. ``STATUS:TODO``


Backups
~~~~~~~

``STATUS:TODO``

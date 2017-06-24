Security considerations
=======================

The CCIW website database stores personal information of various kinds. Because
of this, having a secure site is a very high priority.

In addition, this repo, including this documentation, is publicly readable (on
BitBucket and possible elsewhere). This imposes further constraints on personal
information.

A longer document on the security procedures observed by CCIW is available
outside this repository, "CCIW website security procedures". The contents of
that document need to be understood. It also contains more information on the
different groups of access to the website database, and access to 3rd party
services.

Regarding things more directly touching development of code in this repo, the
following points must be observed:

* Security of the system must not depend on "security by obscurity". This is
  always a bad idea, and in our case we have no obscurity as the source code is
  public.

* All access to the website must be encrypted - using HTTPS for web access,
  and SSH for server access.

* The source code in this project should not contain any information that is
  private to CCIW and specific to the deployment of this project. This includes
  all passwords and API keys. These should instead be stored in the file
  ``config/secrets.json``, and transferred when necessary as per the procedures
  in "CCIW website security procedures".

* The source code must not contain personal information - for example the names
  email addresses or name of people to be emailed in different circumstances.
  Instead, these should be stored:

  * In the database, usually making these values configurable via the Django admin
    by people with appropriate permission levels.

  * In 3rd party services - for example, you might send emails to a
    ``@cciw.co.uk`` alias and configure the recipients manually in Mailgun.

  * In ``secrets.json`` as a last resort.

* Retention of all personal data must be done in accord with the relevant data
  protection laws, and CCIW's own data protection policy (external to this
  repo).

* Access to all officer functionality must be controlled on a "need to know
  basis". The primary places where these are controlled are:

  * permission related methods on the ``User`` model in `</cciw/accounts/models.py>`_
  * permission decorators on views in `</cciw/officers/views.py>`_
  * definitions of group permissions in `</config/groups.yaml>`_
  * other functions in `</cciw/auth.py>`_

* As much as possible, privileged access roles should be determined dynamically,
  rather than by manual configuration of permission groups. For example, by linking
  the ``User``, ``Camp`` and ``Person`` models, we can dynamically determine
  whether a ``User`` account is a leader of a current camp, rather than by
  having to maintain a group “leaders of current camps”.

* If dynamic roles are not possible, we can create groups for additional
  permissions. We don't add individual permissions to User accounts.

* Privileged access must be limited in time - for example, being a leader one
  year does not mean a person should have higher access in subsequent years.

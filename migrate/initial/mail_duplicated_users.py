#!/usr/bin/python

import devel

from django.core import mail
from changed_users import changed


for email, (kept_name, changed_names) in changed.items():
    changed_str = ''.join("   " + n + "\n" for n in changed_names)

    print "Sending to email %s" % email
    mail.send_mail("CCIW website user name change", """
Hi,

The CCIW website has recently been upgraded, and in doing some of the
changes, it was noticed that you have signed up with two different
user names but the same e-mail address.  This was never supposed to
happen, and the bug in the system that allowed it has now been
fixed.

To complete the upgrade, the user names with the same e-mail address
have been combined into a single user name. (Which one to use was
decided on the basis of how many posts had been created by that
user, so your most popular user name has been kept).

In your case, the user name that has been kept is:

   %(kept_name)s

The following user names have been removed and won't work any more:

%(changed_str)s

Any related posts or private messages have been transferred to the
new user name, so you won't have lost anything.

If you have forgotten your password, you can get a new password
when you try to log in to the new site:

   http://www.cciw.co.uk/login/

Regards,

Luke

CCIW webmaster


""" % locals(), "webmaster@cciw.co.uk", [email])

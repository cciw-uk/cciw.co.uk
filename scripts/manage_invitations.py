#!/usr/bin/env python2.5
import _cciw_env
import sys
import os
import socket
from optparse import OptionParser

from django.contrib.auth.models import User
from cciw.cciwmain.models import Camp
from cciw.officers.models import Invitation

parser = OptionParser(usage=
"""

       manage_invitations.py <year> <number> <username1> [<username2> ...]
       manage_invitations.py --remove <year> <number> <username1> [<username2> ...]
"""
)

parser.add_option("-r", "--remove", dest="remove", action="store_true", default=False, help="Remove users instead of adding")

def usage_and_exit():
    parser.print_usage()
    sys.exit(1)

def main():
    options, args = parser.parse_args()
    if len(args) < 2:
        usage_and_exit()

    year = int(args[0])
    campnum = int(args[1])

    camp = Camp.objects.get(year=year, number=campnum)
    users = []
    for uname in args[2:]:
        try:
            u = User.objects.get(username=uname)
        except User.DoesNotExist:
            print "Can't find user '%s'" % uname
        users.append(u)

    for user in users:
        if options.remove:
            try:
                inv = Invitation.objects.get(camp=camp.id, officer=user.id)
                inv.delete()
            except Invitation.DoesNotExist:
                pass
        else:
            try:
                Invitation.objects.get(camp=camp.id, officer=user.id)
            except Invitation.DoesNotExist:
                inv = Invitation(camp_id=camp.id, officer_id=user.id)
                inv.save()

if __name__ == '__main__':
    main()

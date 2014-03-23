#!/usr/bin/env python2.5
from optparse import OptionParser
import sys
from django.contrib.auth.models import User
from cciw.cciwmain.models import Person
from cciw.officers.create import create_officer, create_multiple_officers

parser = OptionParser(usage=
"""

       create_officer.py <username> <first_name> <last_name> <email>
OR:    create_officer.py --leader <username> <first_name> <last_name> <email> "<Person name>"
OR:    create_officer.py --update <username> <first_name> <last_name> <email>
OR:    create_officer.py --fromcsv < data.csv
OR:    create_officer.py --fromcsv --dryrun < data.csv
"""
)

parser.add_option("-u", "--update", dest="update", action="store_true", default=False, help="Updates an existing record, resetting password and sending out email again")
parser.add_option("", "--leader", dest="is_leader", action="store_true", default=False, help="Adds/updates this person as a leader, not an officer")
parser.add_option("", "--dryrun", dest="dryrun", action="store_true", default=False, help="Don't touch the database or actually send emails")
parser.add_option("", "--fromcsv", dest="fromcsv", action="store_true", default=False, help="Read data in from CSV file")

def usage_and_exit():
    parser.print_usage()
    sys.exit(1)

def main():
    options, args = parser.parse_args()

    if options.fromcsv:
        if len(args) > 0:
            usage_and_exit()
        if options.is_leader:
            print("'--leader' not valid with '--fromcsv'")
            usage_and_exit()
        csv_data = parse_csv_data(sys.stdin)
        create_multiple_officers(csv_data, options.dryrun, verbose=True)

    else:
        if options.is_leader:
            if len(args) != 5:
                usage_and_exit()
            username, first_name, last_name, email, personname = args
            if personname is not None:
                try:
                    person = Person.objects.get(name=personname)
                except Person.DoesNotExist:
                    print("Person called '%s' does not exist in the database" % personname)
                    sys.exit(1)
            else:
                person = None

            create_officer(username, first_name, last_name, email,
                           update=options.update, is_leader=True,
                           person=person, verbose=True)
        else:
            if len(args) != 4:
                usage_and_exit()
            username, first_name, last_name, email = args
            create_officer(username, first_name, last_name, email,
                           update=options.update, verbose=True)

def parse_csv_data(iterable):
    import csv
    return list(csv.reader(iterable))


if __name__ == '__main__':
    main()

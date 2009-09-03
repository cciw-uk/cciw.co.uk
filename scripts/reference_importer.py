#!/usr/bin/env python

import sys
import re
import datetime
from cciw.officers.models import Reference, ReferenceForm, Application

def import_reference(fname):
    m = re.search("reference_data\.(?P<appid>\d+)\.(?P<refnum>[12])$", fname)
    if m is None:
        sys.stderr.write("Filename '%s' was not in expected format.\n" % fname)
        sys.exit(1)
    print fname
    appid = m.groupdict()['appid']
    refnum = m.groupdict()['refnum']
    data = eval("".join(open(fname).readlines()))
    data['referee_name'] = data['referee_name'].replace("\n", " ")
    app = Application.objects.get(id=appid)
    ref = app.reference_set.get(referee_number=refnum)
    refform = ReferenceForm(**data)
    refform.reference_info = ref
    refform.save()

usage = """Usage:

./reference_importer.py reference_data.<appid>.<refnum>
"""

if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.stderr.write(usage)
        sys.exit(1)
    else:
        import_reference(sys.argv[1])


#!/usr/bin/env python2.5

# This should not be needed, but just in case the server is powered
# off ungracefully while handle_mail.py is running, we have a script
# to clear out old lock files

import os
from datetime import datetime

def main(lockfiles):
    for f in lockfiles:
        delete_old_lock(f)

def delete_old_lock(lockfile):
    try:
        ts = os.path.getctime(lockfile)
        td = datetime.now() - datetime.fromtimestamp(ts)
        # We assume that it will never take more than 1 hour to run
        # handle_mail.py
        if td.days > 0 or td.seconds > 3600:
            os.unlink(lockfile)
    except:
        pass

if __name__ == '__main__':
    import sys
    main(sys.argv[1:])

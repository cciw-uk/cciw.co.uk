#!/usr/bin/env python
import warnings
# warnings.simplefilter("once", PendingDeprecationWarning)
warnings.simplefilter("once", DeprecationWarning)

import os  # noqa
os.environ['DJANGO_SETTINGS_MODULE'] = 'cciw.settings'

from django.core import management  # noqa
if __name__ == "__main__":
    management.execute_from_command_line()

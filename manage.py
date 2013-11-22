#!/usr/bin/env python
import warnings
warnings.simplefilter("always", PendingDeprecationWarning)
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'cciw.settings'
from django.core import management
if __name__ == "__main__":
    management.execute_from_command_line()

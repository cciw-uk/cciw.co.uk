#!/usr/bin/env python
import os
import warnings

warnings.simplefilter("once", PendingDeprecationWarning)
warnings.simplefilter("once", DeprecationWarning)

os.environ["DJANGO_SETTINGS_MODULE"] = "cciw.settings_local"

from django.core import management  # noqa isort:skip

if __name__ == "__main__":
    management.execute_from_command_line()

#!/usr/bin/env python
import warnings
warnings.simplefilter("always", PendingDeprecationWarning)
warnings.simplefilter("always", DeprecationWarning)



# import warnings
# import traceback
# _old_warn = warnings.warn
# def warn(*args, **kwargs):
#     tb = traceback.extract_stack()
#     _old_warn(*args, **kwargs)
#     tb = "".join(traceback.format_list(tb)[:-1])
#     print(tb)

# warnings.warn = warn

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'cciw.settings'
from django.core import management
if __name__ == "__main__":
    management.execute_from_command_line()

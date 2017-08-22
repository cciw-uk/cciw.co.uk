"""
Utilities for dealing with Reference and ReferenceForm
"""


def first_letter_cap(s):
    return s[0].upper() + s[1:]


def reference_present_val(v):
    # presentation function
    if v is False:
        return "No"
    elif v is True:
        return "Yes"
    else:
        return v

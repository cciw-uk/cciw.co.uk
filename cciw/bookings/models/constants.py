from datetime import timedelta

from django.db import models

DEFAULT_COUNTRY = "GB"

KEEP_FINANCIAL_RECORDS_FOR = timedelta(days=3 * 365 + 1)
# By law we're required to keep financial records for 3 years (3 * 365 + one day for a
# possible leap year)
#
# This mean the above constant is used in various `not_in_use()` methods
# relating to payment information. In this context, it define the business
# requirement that we must keep the data for a *minimum* amount of time.

# We also have '3 years' (and '5 years') in data_retention.yaml. In that
# context, it defines time periods we choose to automatically erase some data
# (though we don't necessarily have to, depending on other concerns).

# For the case of erasure requests under "right to erasure" laws, the values
# defined in data_retention.yaml are not applied (since they define automatic
# erasure, not manual ones), which is why they must also be present in
# `not_in_use()` methods.


class Sex(models.TextChoices):
    MALE = "m", "Male"
    FEMALE = "f", "Female"

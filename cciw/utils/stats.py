from datetime import date
from typing import Any

import pandas as pd
from pandas.core.series import Series


def accumulate(value_list: list[Any | date], index_class: type = pd.Index) -> Series:
    return index_class(value_list).value_counts().sort_index().cumsum()


def accumulate_dates(date_list: list[Any | date]) -> Series:
    return accumulate(date_list, index_class=pd.DatetimeIndex)


def counts(value_list):
    return pd.Index(value_list).value_counts().sort_index()

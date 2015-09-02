import pandas as pd


def accumulate(value_list, index_class=pd.Index):
    return index_class(value_list).value_counts().sort_index().cumsum()


def accumulate_dates(date_list):
    return accumulate(date_list, index_class=pd.DatetimeIndex)

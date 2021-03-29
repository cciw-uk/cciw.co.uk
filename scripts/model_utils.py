# Utils for displaying data at a Python prompt,
#
# Dependencies:
#  pytest
#  visidata >= 2.0

import shutil
from datetime import date

import texttable
import visidata
import visidata.pyobj
from _pytest.assertion.util import _compare_eq_iterable
from django.db.models import QuerySet
from django.db.models.query import ValuesIterable, ValuesListIterable


def get_main_attrs(instance):
    if hasattr(instance, '_meta'):
        return meta_to_col_list(instance._meta)
    elif hasattr(instance, '__attrs_attrs__'):
        return [(field.name, field.type or visidata.anytype)
                for field in instance.__attrs_attrs__]
    return []


def instance_list_table(instances, screen_width=None):
    if not instances:
        return ''
    if screen_width is None:
        screen_width = shutil.get_terminal_size().columns

    table = texttable.Texttable(max_width=screen_width)
    headers = [name for name, _ in get_main_attrs(instances[0])]
    table.add_row(headers)
    for instance in instances:
        table.add_row([getattr(instance, attr) for attr in headers])
    return table.draw()


def meta_to_col_list(_meta):
    retval = []
    for field in _meta.get_fields():
        if not hasattr(field, 'get_attname'):
            continue
        if getattr(field, 'many_to_many', False):
            continue
        retval.append((field.get_attname(), django_to_vd_type(field)))
    return retval


def django_to_vd_type(field):
    return {
        'AutoField': int,
        'BigAutoField': int,
        'BigIntegerField': int,
        'BooleanField': int,
        'DateField': date,
        'DecimalField': float,
        'FloatField': float,
        'ForeignKey': int,  # good enough for now...
        'PositiveIntegerField': int,
        'PositiveSmallIntegerField': int,
        'SmallIntegerField': int,
        'CharField': str,
        'TextField': str,
    }.get(field.get_internal_type(), visidata.anytype)


class QuerySetSheet(visidata.Sheet):
    rowtype = 'rows'  # rowdef: model instance

    @visidata.asyncthread
    def reload(self):
        self.rows = []
        self.columns = []
        if self.source._iterable_class is ValuesIterable:
            for name in self.source._fields:
                self.addColumn(visidata.ItemColumn(name))
        elif self.source._iterable_class is ValuesListIterable:
            for i, name in enumerate(self.source._fields):
                self.addColumn(visidata.ItemColumn(name=name, key=i))
        else:
            for name, t in meta_to_col_list(self.source.model._meta):
                self.addColumn(visidata.AttrColumn(name, type=t))
        for item in visidata.Progress(self.source.iterator(), total=self.source.count()):
            self.addRow(item)


class AutoSheet(visidata.TableSheet):
    rowtype = 'rows'  # rowdef: attrs instance

    @visidata.asyncthread
    def reload(self):
        self.columns = []
        if len(self.source) == 0:
            return
        if isinstance(self.source[0], list):
            for i in range(0, len(self.source[0])):
                self.addColumn(visidata.ItemColumn(key=i, name=str(i)))
        else:
            for name, t in get_main_attrs(self.source[0]):
                self.addColumn(visidata.AttrColumn(name, type=t))
        for row in self.source:
            self.addRow(row)


def vd(objects):
    """
    Wrapper around visidata.run with custom sheet types
    """
    sheet = None
    if isinstance(objects, QuerySet):
        sheet = QuerySetSheet(objects.model.__name__, source=objects)
    elif isinstance(objects, list) and len(objects) > 0:
        instance = objects[0]
        sheet = AutoSheet(instance.__class__.__name__, source=objects)
    if sheet is None:
        sheet = visidata.load_pyobj('', objects)

    return visidata.run(sheet)


def compare_iterables(obj1, obj2):
    print('\n'.join(_compare_eq_iterable(obj1, obj2, verbose=True)))

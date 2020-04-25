# URL path converters
import typing

from .cciwmain.common import CampId


class FourDigitYearConverter:
    regex = '[0-9]{4}'

    def to_python(self, value) -> int:
        return int(value)

    def to_url(self, value):
        return '%04d' % value


class TwoDigitMonthConverter:
    regex = '[0-9]{2}'

    def to_python(self, value) -> int:
        return int(value)

    def to_url(self, value):
        return '%02d' % value


class CampIdConverter:
    regex = r'\d{4}-[^/]+'

    @staticmethod
    def to_python(value) -> CampId:
        year, slug = value.split('-', 1)
        return CampId(int(year), slug)

    @staticmethod
    def to_url(value):
        year, slug = value
        return "{0}-{1}".format(year, slug)


class CampIdListConverter:
    regex = r'{0}(,{1})*'.format(CampIdConverter.regex, CampIdConverter.regex)

    def to_python(self, value) -> typing.List[CampId]:
        return [
            CampIdConverter.to_python(camp_id_str)
            for camp_id_str in value.split(',')
        ]

    def to_url(self, value):
        return ','.join(
            CampIdConverter.to_url(camp_id)
            for camp_id in value
        )


class OptStr:
    """
    Optional string - zero or more characters, excluding /
    """
    regex = r'[^/]*'

    def to_python(self, value) -> str:
        return value

    def to_url(self, value):
        return value

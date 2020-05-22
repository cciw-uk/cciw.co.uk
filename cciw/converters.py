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
        return CampId.from_url_part(value)

    @staticmethod
    def to_url(value: CampId):
        return str(value)


class CampIdListConverter:
    regex = f'{CampIdConverter.regex}(,{CampIdConverter.regex})*'

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

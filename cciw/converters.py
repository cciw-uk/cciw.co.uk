# URL path converters


class FourDigitYearConverter:
    regex = '[0-9]{4}'

    def to_python(self, value):
        return int(value)

    def to_url(self, value):
        return '%04d' % value


class TwoDigitMonthConverter:
    regex = '[0-9]{2}'

    def to_python(self, value):
        return int(value)

    def to_url(self, value):
        return '%02d' % value


class CampIdList:
    regex = r'\d{4}-[^/]+(,\d{4}-[^/]+)*'

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


class OptStr:
    """
    Optional string - zero or more characters, excluding /
    """
    regex = r'[^/]*'

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value

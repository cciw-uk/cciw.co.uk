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


class CampId:
    regex = r'\d{4}-[^/]+'

    @staticmethod
    def to_python(value):
        year, slug = value.split('-', 1)
        return int(year), slug

    @staticmethod
    def to_url(value):
        year, slug = value
        return "{0}-{1}".format(year, slug)


class CampIdList:
    regex = r'{0}(,{1})*'.format(CampId.regex, CampId.regex)

    def to_python(self, value):
        return [
            CampId.to_python(camp_id_str)
            for camp_id_str in value.split(',')
        ]

    def to_url(self, value):
        return ','.join(
            CampId.to_url(camp_id)
            for camp_id in value
        )


class OptStr:
    """
    Optional string - zero or more characters, excluding /
    """
    regex = r'[^/]*'

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value

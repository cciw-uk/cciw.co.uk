# URL path converters


from .cciwmain.common import CampId


class FourDigitYearConverter:
    regex = "[0-9]{4}"

    def to_python(self, value: str) -> int:
        return int(value)

    def to_url(self, value: int) -> str:
        return f"{value:04}"


class TwoDigitMonthConverter:
    regex = "[0-9]{2}"

    def to_python(self, value: str) -> int:
        return int(value)

    def to_url(self, value: int):
        return f"{value:02}"


class CampIdConverter:
    # See also CampId.__str__
    regex = r"\d{4}-[^/]+"

    @staticmethod
    def to_python(value: str) -> CampId:
        year, slug = value.split("-", 1)
        return CampId(int(year), slug)

    @staticmethod
    def to_url(value: CampId) -> str:
        return str(value)


class CampIdListConverter:
    regex = f"{CampIdConverter.regex}(,{CampIdConverter.regex})*"

    def to_python(self, value) -> list[CampId]:
        return [CampIdConverter.to_python(camp_id_str) for camp_id_str in value.split(",")]

    def to_url(self, value: list[CampId]) -> str:
        return ",".join(CampIdConverter.to_url(camp_id) for camp_id in value)


class OptInt:
    """
    Optional int - zero or digits, converted to None if zero length
    """

    regex = r"\d*"

    def to_python(self, value: str) -> int | None:
        return None if value == "" else int(value)

    def to_url(self, value: int | None) -> str:
        return "" if value is None else str(value)

from datetime import date, timedelta

from cciw.accounts.models import User
from cciw.cciwmain.models import Camp, CampName, Person, Site
from cciw.officers.models import CampRole
from cciw.utils.tests.factories import Auto


def create_camp(
    *,
    start_date: date = Auto,
    end_date: date = Auto,
    site: Site = Auto,
    camp_name: str | CampName = Auto,
    minimum_age: int = Auto,
    maximum_age: int = Auto,
    year: int = Auto,
    leader: Person | User | bool = Auto,
    leaders: list[Person | User] = Auto,
    chaplain: Person | User = Auto,
    future: bool = Auto,
    officers: list[User] = Auto,
    officers_role: CampRole | str = Auto,
    max_campers: int = 80,
    max_male_campers: int = 60,
    max_female_campers: int = 60,
    last_booking_date: date | None = None,
) -> Camp:
    assert not (leader is not Auto and leaders is not Auto), "Only supply one of 'leaders' and 'leader'"
    if leader:
        if leader is True:
            from cciw.officers.tests import factories as officers_factories

            leader = officers_factories.create_officer()
        leaders = [leader]
    elif not leaders:
        leaders = []

    if future is not Auto:
        assert start_date is Auto and end_date is Auto and year is Auto

    if start_date is Auto:
        if end_date is not Auto:
            start_date = end_date - timedelta(days=7)
        else:
            if year is not Auto:
                # Some date in the summer
                start_date = date(year, 8, 1)
            else:
                if future:
                    start_date = date.today() + timedelta(days=365)
                else:
                    start_date = date.today()
    if end_date is Auto:
        end_date = start_date + timedelta(days=7)
    site = site or get_any_site()
    if minimum_age is Auto:
        if maximum_age is not Auto:
            minimum_age = maximum_age - 6
        else:
            minimum_age = 11
    if maximum_age is Auto:
        maximum_age = minimum_age + 6
    if year is not Auto:
        assert year == start_date.year
    else:
        year = start_date.year

    if isinstance(camp_name, str):
        camp_name = get_or_create_camp_name(camp_name)
    elif camp_name is Auto:
        camp_name = _get_non_clashing_camp_name(year)

    camp = Camp.objects.create(
        end_date=end_date,
        camp_name=camp_name,
        site=site,
        minimum_age=minimum_age,
        maximum_age=maximum_age,
        year=year,
        start_date=start_date,
        chaplain=make_into_person(chaplain) if chaplain else None,
        max_campers=max_campers,
        max_male_campers=max_male_campers,
        max_female_campers=max_female_campers,
        last_booking_date=last_booking_date,
    )
    if leaders:
        set_camp_leaders(camp, leaders)
    if officers:
        from cciw.officers.tests import factories as officers_factories

        officers_factories.add_officers_to_camp(camp, officers, role=officers_role)
    return camp


def _get_non_clashing_camp_name(year: int) -> CampName:
    # We have a unique constraint on name/year that we
    # need to respect to be able to create new camps.
    years_camps = Camp.objects.filter(year=year)
    name = _get_next_camp_name(excluding=[camp.camp_name.name for camp in years_camps])
    return get_or_create_camp_name(name)


def _get_next_camp_name(excluding: list[str] | None = None) -> str:
    available_names = set(COLORS.keys())
    if excluding:
        available_names -= set(excluding)
    return sorted(available_names)[0]


def get_any_camp() -> Camp:
    camp = Camp.objects.order_by("id").first()
    if camp is not None:
        return camp
    return create_camp()


def create_camp_name(*, name: str = Auto, color: str = Auto) -> CampName:
    name = name or _get_next_camp_name()
    color = color or COLORS.get(name, "#ff0000")
    camp_name = CampName.objects.create(
        name=name,
        slug=name.lower().replace(" ", "-"),
        color=color,
    )
    return camp_name


def get_any_camp_name():
    camp_name = CampName.objects.order_by("id").first()
    if camp_name is not None:
        return camp_name
    return create_camp_name()


def get_or_create_camp_name(name: str) -> CampName:
    try:
        return CampName.objects.get(name=name)
    except CampName.DoesNotExist:
        return create_camp_name(name=name)


def create_site(
    *,
    short_name: str = Auto,
    long_name: str = Auto,
) -> Site:
    return Site.objects.create(
        short_name=short_name or "The Farm",
        long_name=long_name or "The Farm in the Valley",
        slug_name="the-farm",
        info="A really lovely farm.",
    )


def get_any_site() -> Site:
    site = Site.objects.order_by("id").first()
    if site is not None:
        return site
    return create_site()


def set_camp_leaders(camp: Camp, leaders: list[User | Person]) -> None:
    camp.leaders.set([make_into_person(leader) for leader in leaders])


def get_any_camp_leader() -> Person:
    from cciw.officers.tests import factories as officer_factories

    person = Person.objects.first()
    if not person:
        user = officer_factories.get_any_officer()
        person = make_into_person(user)
    return person


def make_into_person(user_or_person: Person | User) -> Person:
    if isinstance(user_or_person, User):
        user = user_or_person
        matching_people = [p for p in user.people.all() if set(p.users.all()) == {user}]
        if matching_people:
            return matching_people[0]
        person = create_person(name=user.full_name)
        person.users.set([user])
        return person
    elif isinstance(user_or_person, Person):
        return user_or_person
    else:
        raise NotImplementedError(f"Don't know what to do with {user_or_person}")


def create_person(*, name: str = Auto) -> Person:
    return Person.objects.create(
        name=name or "A Person",
    )


def create_and_add_leaders(
    camp: Camp, *, count: int, email_template="leader{n}@example.com", username_template="leader{n}"
) -> list[tuple[Person, User]]:
    retval = []
    for n in range(1, count + 1):
        leader = Person.objects.create(name=f"Leader{n}")
        leader_user = User.objects.create(username=username_template.format(n=n), email=email_template.format(n=n))
        leader.users.add(leader_user)
        camp.leaders.add(leader)
        retval.append((leader, leader_user))

    return retval


def add_camp_leader(camp: Camp, user_or_person: Person | User) -> None:
    person = make_into_person(user_or_person)
    camp.leaders.add(person)


# Large list of names/colors we can use for creating CampName, especially for
# cases where we create lots of camps for performance testing.
COLORS = {
    "Red": "#FF0000",
    "Aero": "#7CB9E8",
    "Alabaster": "#EDEAE0",
    "Almond": "#EFDECD",
    "Amaranth": "#E52B50",
    "Amazon": "#3B7A57",
    "Amber": "#FFBF00",
    "Amethyst": "#9966CC",
    "Apricot": "#FBCEB1",
    "Aqua": "#00FFFF",
    "Aquamarine": "#7FFFD4",
    "Artichoke": "#8F9779",
    "Asparagus": "#87A96B",
    "Auburn": "#A52A2A",
    "Aureolin": "#FDEE00",
    "Avocado": "#568203",
    "Azure": "#007FFF",
    "Beaver": "#9F8170",
    "Beige": "#F5F5DC",
    "Bisque": "#FFE4C4",
    "Bistre": "#3D2B1F",
    "Bittersweet": "#FE6F5E",
    "Black": "#000000",
    "Blond": "#FAF0BE",
    "Blue": "#0000FF",
    "Bluetiful": "#3C69E7",
    "Blush": "#DE5D83",
    "Bole": "#79443B",
    "Bone": "#E3DAC9",
    "Brandy": "#87413F",
    "Bronze": "#CD7F32",
    "Brown": "#88540B",
    "Buff": "#FFC680",
    "Burgundy": "#800020",
    "Burlywood": "#DEB887",
    "Byzantine": "#BD33A4",
    "Byzantium": "#702963",
    "Cadet": "#536872",
    "Camel": "#C19A6B",
    "Canary": "#FFFF99",
    "Capri": "#00BFFF",
    "Cardinal": "#C41E3A",
    "Carmine": "#960018",
    "Carnelian": "#B31B1B",
    "Catawba": "#703642",
    "Celadon": "#ACE1AF",
    "Celeste": "#B2FFFF",
    "Cerise": "#DE3163",
    "Cerulean": "#007BA7",
    "Champagne": "#F7E7CE",
    "Charcoal": "#36454F",
    "Chestnut": "#954535",
    "Cinereous": "#98817B",
    "Cinnabar": "#E34234",
    "Citrine": "#E4D00A",
    "Citron": "#9FA91F",
    "Claret": "#7F1734",
    "Coffee": "#6F4E37",
    "Copper": "#B87333",
    "Coquelicot": "#FF3800",
    "Coral": "#FF7F50",
    "Cordovan": "#893F45",
    "Corn": "#FBEC5D",
    "Cornsilk": "#FFF8DC",
    "Cream": "#FFFDD0",
    "Crimson": "#DC143C",
    "Crystal": "#A7D8DE",
    "Cultured": "#F5F5F5",
    "Cyan": "#00FFFF",
    "Cyclamen": "#F56FA1",
    "Denim": "#1560BD",
    "Desert": "#C19A6B",
    "Drab": "#967117",
    "Ebony": "#555D50",
    "Ecru": "#C2B280",
    "Eggplant": "#614051",
    "Eggshell": "#F0EAD6",
    "Eigengrau": "#16161D",
    "Emerald": "#50C878",
    "Eminence": "#6C3082",
    "Erin": "#00FF40",
    "Fallow": "#C19A6B",
    "Fandango": "#B53389",
    "Fawn": "#E5AA70",
    "Feldgrau": "#4D5D53",
    "Firebrick": "#B22222",
    "Flame": "#E25822",
    "Flax": "#EEDC82",
    "Flirt": "#A2006D",
    "Frostbite": "#E936A7",
    "Fuchsia": "#FF00FF",
    "Fulvous": "#E48400",
}

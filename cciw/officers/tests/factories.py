from datetime import date, datetime

from django.utils import timezone

from cciw.accounts.models import (
    BOOKING_SECRETARY_ROLE_NAME,
    DBS_OFFICER_ROLE_NAME,
    REFERENCE_CONTACT_ROLE_NAME,
    SECRETARY_ROLE_NAME,
    Role,
    User,
    setup_auth_roles,
)
from cciw.cciwmain.models import Camp
from cciw.contact_us.models import Message
from cciw.officers.models import Application, Referee, Reference
from cciw.utils.tests.factories import Auto, sequence

USERNAME_SEQUENCE = sequence(lambda n: f"auto_user_{n}")


BOOKING_SECRETARY_USERNAME = "bookingsec"
BOOKING_SECRETARY_PASSWORD = "a_password"
BOOKING_SECRETARY = (BOOKING_SECRETARY_USERNAME, BOOKING_SECRETARY_PASSWORD)


SECRETARY_USERNAME = "mrsecretary"
SECRETARY_PASSWORD = "test_password"
SECRETARY = (SECRETARY_USERNAME, SECRETARY_PASSWORD)


DBSOFFICER_USERNAME = "mrsdbsofficer"
DBSOFFICER_PASSWORD = "my_password"
DBSOFFICER_EMAIL = "dbsofficer@somewhere.com"
DBSOFFICER = (DBSOFFICER_USERNAME, DBSOFFICER_PASSWORD)


def create_officer(
    username: str = Auto,
    first_name: str = "Joe",
    last_name: str = "Bloggs",
    is_active: bool = True,
    is_superuser: bool = False,
    is_staff: bool = True,
    email: str = Auto,
    password: str = Auto,
    roles: list[Role] = Auto,
    contact_phone_number: str = "",
) -> User:
    username = username or next(USERNAME_SEQUENCE)
    email = email or f"{username}@example.com"

    user = User(
        username=username,
        first_name=first_name,
        last_name=last_name,
        is_active=is_active,
        is_superuser=is_superuser,
        is_staff=is_staff,
        email=email,
        contact_phone_number=contact_phone_number,
    )
    if password is Auto:
        password = "test_normaluser_password"  # OFFICER_PASSWORD TODO needed?
    if password is not None:
        user.set_password(password)
    user.save()
    if roles:
        user.roles.set(roles)
    return user


def create_leader(**kwargs) -> User:
    # A leader is just an officer. No special roles are involved,
    # only the association to a camp via a `Person` record.
    return create_officer(**kwargs)


def get_any_officer() -> User:
    user = User.objects.filter(is_staff=True).first()
    if not user:
        return create_officer()
    return user


def add_officers_to_camp(camp: Camp, officers: list[User]) -> None:
    for officer in officers:
        camp.invitations.create(officer=officer)


def _get_standard_role(name: str) -> Role:
    try:
        return Role.objects.get(name=name)
    except Role.DoesNotExist:
        # setup_auth_roles() is normally done on deployment, so we can rely
        # on these Role objects normally existing in the database, like
        # fixtures:
        setup_auth_roles()
        return Role.objects.get(name=name)


def create_booking_secretary() -> User:
    return create_officer(
        username=BOOKING_SECRETARY_USERNAME,
        roles=[_get_standard_role(BOOKING_SECRETARY_ROLE_NAME)],
        password=BOOKING_SECRETARY_PASSWORD,
    )


def create_secretary() -> User:
    return create_officer(
        username=SECRETARY_USERNAME,
        roles=[_get_standard_role(SECRETARY_ROLE_NAME)],
        password=SECRETARY_PASSWORD,
    )


def create_dbs_officer() -> User:
    return create_officer(
        username=DBSOFFICER_USERNAME,
        email=DBSOFFICER_EMAIL,
        roles=[_get_standard_role(DBS_OFFICER_ROLE_NAME)],
        password=DBSOFFICER_PASSWORD,
    )


def create_safeguarding_coordinator() -> User:
    return create_officer(
        username="safeguarder",
        first_name="Safe",
        last_name="Guarder",
        contact_phone_number="01234 567890",
        roles=[_get_standard_role(REFERENCE_CONTACT_ROLE_NAME)],
    )


def create_application(
    officer: User = Auto,
    *,
    year: int = Auto,
    date_saved: date = Auto,
    full_name: str = Auto,
    address_firstline: str = Auto,
    birth_date: date = Auto,
    dbs_number: str = "",
    dbs_check_consent: bool = True,
    referee1_overrides: dict = Auto,
    referee2_overrides: dict = Auto,
    finished=True,
) -> Application:
    if date_saved is Auto:
        if year is not Auto:
            date_saved = datetime(year, 1, 1)
        else:
            date_saved = timezone.now().date()

    if officer is Auto:
        officer = get_any_officer()
    if full_name is Auto:
        full_name = "Joe Winston Bloggs"
    fields = dict(
        officer=officer,
        address_country="UK",
        address_county="Yorkshire",
        address_email="hey@boo.com",
        address_firstline="654 Stupid Way" if address_firstline is Auto else address_firstline,
        address_mobile="",
        address_postcode="XY9 8WN",
        address_tel="01048378569",
        address_town="Bradford",
        allegation_declaration=False,
        birth_date=birth_date or "1911-02-07",
        birth_place="Foobar",
        christian_experience="Became a Christian at age 0.2 years",
        concern_declaration=False,
        concern_details="",
        court_declaration=False,
        court_details="",
        dbs_check_consent=dbs_check_consent,
        dbs_number=dbs_number,
        crime_declaration=False,
        crime_details="",
        date_saved=date_saved,
        finished=finished,
        full_name=full_name,
        illness_details="",
        relevant_illness=False,
        youth_experience="Lots",
        youth_work_declined=False,
        youth_work_declined_details="",
    )
    application = Application.objects.create(**fields)
    for referee_number, ref_overrides in zip([1, 2], [referee1_overrides, referee2_overrides]):
        referee_fields = dict(
            referee_number=referee_number,
            address=f"Referee {referee_number} Address\r\nLine 2",
            email=f"referee{referee_number}@email.co.uk",
            mobile="",
            name=f"Referee{referee_number} Name",
            tel="01222 666666",
        )
        if ref_overrides:
            referee_fields.update(ref_overrides)

        application.referee_set.create(**referee_fields)
    return application


def create_complete_reference(referee: Referee) -> Reference:
    return Reference.objects.create(
        referee=referee,
        referee_name="Referee1 Name",
        how_long_known="A long time",
        capacity_known="Pastor",
        known_offences=False,
        capability_children="Wonderful",
        character="Almost sinless",
        concerns="Perhaps too good for camp",
        comments="",
        date_created=datetime(2000, 2, 20),
    )


def create_contact_us_message() -> Message:
    return Message.objects.create(
        email="example@example.com",
        message="hello",
    )
from datetime import date, datetime

from django.utils import timezone

from cciw.accounts.models import (
    BOOKING_SECRETARY_ROLE_NAME,
    DBS_OFFICER_ROLE_NAME,
    REFERENCE_CONTACT_ROLE_NAME,
    SECRETARY_ROLE_NAME,
    SITE_EDITOR_ROLE_NAME,
    Role,
    User,
    setup_auth_roles,
)
from cciw.cciwmain.models import Camp
from cciw.contact_us.models import Message
from cciw.officers.models import Application, Qualification, Referee, Reference
from cciw.utils.tests.factories import Auto, sequence

USERNAME_SEQUENCE = sequence(lambda n: f"auto_user_{n}")


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


def create_current_camp_leader():
    from cciw.cciwmain.tests import factories as camps_factories

    leader = create_officer()
    camps_factories.create_camp(leader=leader)
    return leader


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


def create_site_editor() -> User:
    return create_officer(
        roles=[_get_standard_role(SITE_EDITOR_ROLE_NAME)],
    )


def create_booking_secretary() -> User:
    return create_officer(
        roles=[_get_standard_role(BOOKING_SECRETARY_ROLE_NAME)],
    )


def create_secretary() -> User:
    return create_officer(
        roles=[_get_standard_role(SECRETARY_ROLE_NAME)],
    )


def create_dbs_officer() -> User:
    return create_officer(
        roles=[_get_standard_role(DBS_OFFICER_ROLE_NAME)],
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
    referee1_name: str = Auto,
    referee1_email: str = Auto,
    referee1_address: str = Auto,
    referee1_tel: str = Auto,
    referee1_capacity_known: str = Auto,
    referee2_name: str = Auto,
    referee2_email: str = Auto,
    referee2_address: str = Auto,
    referee2_tel: str = Auto,
    referee2_capacity_known: str = Auto,
    finished=True,
    qualifications: list[Qualification] = Auto,
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
    application.referee_set.create(
        referee_number=1,
        address=referee1_address or "Referee 1 Address\r\nLine 2",
        email=f"{officer.username}-referee1@email.co.uk" if referee1_email is Auto else referee1_email,
        mobile="",
        name="Referee1 Name" if referee1_name is Auto else referee1_name,
        tel="01222 666661" if referee1_tel is Auto else referee1_tel,
        capacity_known="Pastor" if referee1_capacity_known is Auto else referee1_capacity_known,
    )
    application.referee_set.create(
        referee_number=2,
        address=referee2_address or "Referee 2 Address\r\nLine 2",
        email=f"{officer.username}-referee2@email.co.uk" if referee2_email is Auto else referee2_email,
        mobile="",
        name="Referee2 Name" if referee2_name is Auto else referee2_name,
        tel="01222 666662" if referee2_tel is Auto else referee2_tel,
        capacity_known="Youth leader" if referee2_capacity_known is Auto else referee1_capacity_known,
    )
    if qualifications:
        for qual in qualifications:
            if qual.application_id is None:
                qual.application = application
                qual.save()

    return application


def create_complete_reference(referee: Referee) -> Reference:
    return Reference.objects.create(
        referee=referee,
        referee_name=referee.name,
        how_long_known="A long time",
        capacity_known="Pastor",
        known_offences=False,
        capability_children="Wonderful",
        character="Almost sinless",
        concerns="Perhaps too good for camp",
        comments="",
        date_created=date.today(),
    )


def create_contact_us_message() -> Message:
    return Message.objects.create(
        email="example@example.com",
        message="hello",
    )

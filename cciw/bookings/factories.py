from datetime import date
from decimal import Decimal

from django.conf import settings
from django.utils import timezone
from paypal.standard.ipn.models import PayPalIPN

from cciw.bookings.models import (
    Booking,
    BookingAccount,
    BookingState,
    CustomAgreement,
    ManualPayment,
    ManualPaymentType,
    Price,
    PriceType,
    RefundPayment,
    SupportingInformation,
    SupportingInformationDocument,
    SupportingInformationType,
    WriteOffDebt,
    build_paypal_custom_field,
)
from cciw.cciwmain.models import Camp
from cciw.cciwmain.tests import factories as camps_factories
from cciw.utils.tests.factories import Auto, sequence

BOOKING_ACCOUNT_EMAIL_SEQUENCE = sequence(lambda n: f"booker_{n}@example.com")


def create_booking(
    # From user fields, order same as booking form.
    # TODO we are missing a few (non required) fields here
    *,
    account: BookingAccount = Auto,
    camp: Camp = Auto,
    price_type: PriceType = PriceType.FULL,
    first_name: str = Auto,
    last_name: str = Auto,
    name: str = Auto,
    sex: str = "m",
    birth_date: date = Auto,
    address_line1="123 My street",
    address_city="Metrocity",
    address_country="GB",
    address_post_code="ABC 123",
    contact_name="Mr Father",
    contact_line1="98 Main Street",
    contact_city="Metrocity",
    contact_country="GB",
    contact_post_code="ABC 456",
    contact_phone_number="01982 987654",
    gp_name="Doctor Who",
    gp_line1="The Tardis",
    gp_city="London",
    gp_country="GB",
    gp_post_code="SW1 1PQ",
    gp_phone_number="01234 456789",
    medical_card_number="asdfasdf",
    last_tetanus_injection_date=Auto,
    serious_illness=False,
    agreement=True,
    # Internal fields
    state=BookingState.INFO_COMPLETE,
    amount_due=Auto,
) -> Booking:
    account = account or create_booking_account()
    camp = camp or camps_factories.get_any_camp()
    if birth_date is Auto:
        birth_date = date(date.today().year - camp.minimum_age - 2, 1, 1)
    # Prices are pre-condition for creating booking in normal situation
    create_prices(year=camp.year)
    if name is not Auto:
        assert first_name is Auto
        assert last_name is Auto
        first_name, last_name = name.split(" ")
    else:
        first_name = first_name or "Frédéric"
        last_name = last_name or "Bloggs"
    if last_tetanus_injection_date is Auto:
        last_tetanus_injection_date = date(camp.year - 5, 2, 3)

    booking: Booking = Booking.objects.create(
        account=account,
        camp=camp,
        price_type=price_type,
        first_name=first_name,
        last_name=last_name,
        sex=sex,
        birth_date=birth_date,
        address_line1=address_line1,
        address_city=address_city,
        address_country=address_country,
        address_post_code=address_post_code,
        contact_name=contact_name,
        contact_line1=contact_line1,
        contact_city=contact_city,
        contact_country=contact_country,
        contact_post_code=contact_post_code,
        contact_phone_number=contact_phone_number,
        gp_name=gp_name,
        gp_line1=gp_line1,
        gp_city=gp_city,
        gp_country=gp_country,
        gp_post_code=gp_post_code,
        gp_phone_number=gp_phone_number,
        medical_card_number=medical_card_number,
        last_tetanus_injection_date=last_tetanus_injection_date,
        serious_illness=serious_illness,
        agreement=agreement,
        state=state,
        amount_due=Decimal(0) if amount_due is Auto else amount_due,
    )
    if amount_due is Auto:
        booking.auto_set_amount_due()
        booking.save()
    booking.update_approvals()
    return booking


def create_booking_account(
    *,
    name: str = "A Booker",
    address_line1: str = "",
    address_post_code: str = "XYZ",
    email: str = Auto,
) -> BookingAccount:
    return BookingAccount.objects.create(
        name=name,
        email=email or next(BOOKING_ACCOUNT_EMAIL_SEQUENCE),
        address_line1=address_line1,
        address_post_code=address_post_code,
    )


def create_processed_payment(
    *,
    account: BookingAccount = Auto,
    amount=1,
):
    manual_payment = create_manual_payment(account=account, amount=amount)
    payment = manual_payment.paymentsource.payment
    payment.refresh_from_db()
    assert payment.processed_at  # should have been done via process_all_payments via signals
    return payment


def create_manual_payment(
    *,
    account: BookingAccount = Auto,
    amount=1,
):
    return ManualPayment.objects.create(
        account=account or create_booking_account(),
        amount=amount,
        payment_type=ManualPaymentType.CHEQUE,
    )


def create_refund_payment(
    *,
    account: BookingAccount = Auto,
    amount=1,
):
    return RefundPayment.objects.create(
        account=account or create_booking_account(),
        amount=amount,
        payment_type=ManualPaymentType.CHEQUE,
    )


def create_write_off_debt_payment(
    *,
    account: BookingAccount = Auto,
    amount=0,
):
    return WriteOffDebt.objects.create(
        account=account or create_booking_account(),
        amount=amount,
    )


def create_ipn(
    *,
    account: BookingAccount | None = None,
    custom: str = Auto,
    payer_email: str = Auto,
    amount: Decimal | int = Auto,
    **kwargs,
):
    if account:
        assert custom is Auto
        custom = build_paypal_custom_field(account)
    else:
        custom = custom or ""
    defaults = dict(
        mc_gross=Decimal("1.00") if amount is Auto else Decimal(amount),
        custom=custom,
        ipaddress="127.0.0.1",
        payment_status="Completed",
        txn_id="1",
        business=settings.PAYPAL_RECEIVER_EMAIL,
        payment_date=timezone.now(),
        payer_email="" if payer_email is Auto else payer_email,
    )
    defaults.update(kwargs)
    ipn = PayPalIPN.objects.create(**defaults)
    ipn.send_signals()
    return ipn


def create_custom_agreement(*, year, name, text_html="Text"):
    return CustomAgreement.objects.create(
        year=year,
        name=name,
        text_html=text_html,
        active=True,
    )


def create_prices(*, year, deposit=Auto, early_bird_discount=Auto, full_price=Auto):
    if deposit is Auto:
        deposit = Decimal(20)
    else:
        deposit = Decimal(deposit)
    if early_bird_discount is Auto:
        early_bird_discount = Decimal(10)
    else:
        early_bird_discount = Decimal(early_bird_discount)
    if full_price is Auto:
        full_price = Decimal(100)
    else:
        full_price = Decimal(full_price)
    price_full = Price.objects.get_or_create(year=year, price_type=PriceType.FULL, price=full_price)[0].price
    price_2nd_child = Price.objects.get_or_create(year=year, price_type=PriceType.SECOND_CHILD, price=Decimal("75"))[
        0
    ].price
    price_3rd_child = Price.objects.get_or_create(year=year, price_type=PriceType.THIRD_CHILD, price=Decimal("50"))[
        0
    ].price
    price_deposit = Price.objects.get_or_create(year=year, price_type=PriceType.DEPOSIT, defaults={"price": deposit})[
        0
    ].price
    price_early_bird_discount = Price.objects.get_or_create(
        year=year, price_type=PriceType.EARLY_BIRD_DISCOUNT, defaults={"price": early_bird_discount}
    )[0].price
    return price_full, price_2nd_child, price_3rd_child, price_deposit, price_early_bird_discount


def create_supporting_information_type(*, name="Test"):
    return SupportingInformationType.objects.create(name=name)


def get_or_create_supporting_information_type():
    return SupportingInformationType.objects.first() or create_supporting_information_type()


def create_supporting_information(
    *,
    booking: Booking = Auto,
    information_type: SupportingInformationType = Auto,
    from_name: str = "Some Person",
    document_filename: str = Auto,
    document_content: bytes = Auto,
    document_mimetype: str = Auto,
):
    if booking is Auto:
        booking = create_booking()
    if any([document_content, document_filename, document_mimetype]):
        if document_filename is Auto:
            document_filename = "test.txt"
        if document_mimetype is Auto:
            document_mimetype = "text/plain"
        if document_content is Auto:
            document_content = b"Hello"
        doc = SupportingInformationDocument.objects.create(
            filename=document_filename,
            content=document_content,
            mimetype=document_mimetype,
        )
    else:
        doc = None
    if information_type is Auto:
        information_type = get_or_create_supporting_information_type()
    supporting_information = SupportingInformation.objects.create(
        booking=booking,
        from_name=from_name,
        information_type=information_type,
        document=doc,
    )

    return supporting_information

import re
from datetime import datetime
from decimal import Decimal

from django.db import models, transaction
from django.utils import timezone
from paypal.standard.ipn.models import PayPalIPN

from .accounts import BookingAccount
from .mixins import NoEditMixin


class ManualPaymentType(models.IntegerChoices):
    CHEQUE = 0, "Cheque"
    CASH = 1, "Cash"
    ECHEQUE = 2, "e-Cheque"
    BACS = 3, "Bank transfer"


class PaymentManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "account",
                "source",
                "source__manual_payment",
                "source__refund_payment",
                "source__write_off_debt",
                "source__account_transfer_payment",
                "source__ipn_payment",
            )
        )

    def received_since(self, since: datetime):
        return self.filter(created_at__gt=since)

    def create(self, source_instance=None, **kwargs):
        if source_instance is not None:
            source = PaymentSource.from_source_instance(source_instance)
            kwargs["source"] = source
        return super().create(**kwargs)


# The Payment object keeps track of all the payments that need to be or have
# been credited to an account. It also acts as a log of everything that has
# happened to the BookingAccount.total_received field. Payment objects are never
# modified or deleted - if, for example, a ManualPayment object is deleted
# because of an entry error, a new (negative) Payment object is created.


class Payment(NoEditMixin, models.Model):
    amount = models.DecimalField(decimal_places=2, max_digits=10)
    account = models.ForeignKey(BookingAccount, related_name="payments", on_delete=models.PROTECT)
    source = models.OneToOneField("PaymentSource", null=True, blank=True, on_delete=models.SET_NULL)
    processed_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField()

    objects = PaymentManager()

    class Meta:
        base_manager_name = "objects"

    def __str__(self):
        if self.source_id is not None and hasattr(self.source.model_source, "payment_description"):
            retval = self.source.model_source.payment_description
        else:
            retval = "Payment: {amount} {from_or_to} {name} via {type}".format(
                amount=abs(self.amount),
                from_or_to="from" if self.amount > 0 else "to",
                name=self.account.name,
                type=self.payment_type,
            )

        return retval

    @property
    def payment_type(self):
        if self.source_id is None:
            return "[deleted]"

        return self.source.payment_type


class ManualPaymentManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related("account")


class ManualPaymentBase(NoEditMixin, models.Model):
    amount = models.DecimalField(decimal_places=2, max_digits=10)
    created_at = models.DateTimeField(default=timezone.now)
    payment_type = models.PositiveSmallIntegerField(choices=ManualPaymentType, default=ManualPaymentType.CHEQUE)

    class Meta:
        abstract = True
        base_manager_name = "objects"


class ManualPayment(ManualPaymentBase):
    account = models.ForeignKey(BookingAccount, on_delete=models.PROTECT, related_name="manual_payments")

    objects = ManualPaymentManager()

    class Meta:
        base_manager_name = "objects"

    def __str__(self):
        return f"Manual payment of £{self.amount} from {self.account}"


class RefundPayment(ManualPaymentBase):
    account = models.ForeignKey(BookingAccount, on_delete=models.PROTECT, related_name="refund_payments")

    objects = ManualPaymentManager()

    class Meta:
        base_manager_name = "objects"

    def __str__(self):
        return f"Refund payment of £{self.amount} to {self.account}"


class WriteOffDebtManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related("account")


class WriteOffDebt(NoEditMixin, models.Model):
    account = models.ForeignKey(BookingAccount, on_delete=models.PROTECT, related_name="write_off_debt")
    amount = models.DecimalField(decimal_places=2, max_digits=10)
    created_at = models.DateTimeField(default=timezone.now)

    objects = WriteOffDebtManager()

    def __str__(self):
        return f"Write off debt of £{self.amount} for {self.account}"

    @property
    def payment_description(self):
        return f"Debt of £{self.amount} written off for {self.account}"

    class Meta:
        base_manager_name = "objects"
        verbose_name = "write-off debt record"
        verbose_name_plural = "write-off debt records"


class AccountTransferPayment(NoEditMixin, models.Model):
    from_account = models.ForeignKey(BookingAccount, on_delete=models.PROTECT, related_name="transfer_from_payments")
    to_account = models.ForeignKey(BookingAccount, on_delete=models.PROTECT, related_name="transfer_to_payments")
    amount = models.DecimalField(decimal_places=2, max_digits=10)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.amount} from {self.from_account} to {self.to_account} on {self.created_at}"

    @property
    def payment_description(self):
        return f"Transfer: {self.amount} transferred from {self.from_account} to {self.to_account}"


type PaymentModel = ManualPayment | RefundPayment | WriteOffDebt | AccountTransferPayment | PayPalIPN


# This model abstracts the different types of payment that can be the source for
# Payment. The real 'source' is the instance pointed to by one of the FKs it
# contains.
class PaymentSource(models.Model):
    # For every different type of payment added with FK below, we need to update:
    # - def payment_type() below
    # - MODEL_MAP below
    # - PaymentManager.get_queryset() above, select_related() call
    # - PaymentModel alias above

    manual_payment = models.OneToOneField(ManualPayment, null=True, blank=True, on_delete=models.CASCADE)
    refund_payment = models.OneToOneField(RefundPayment, null=True, blank=True, on_delete=models.CASCADE)
    write_off_debt = models.OneToOneField(WriteOffDebt, null=True, blank=True, on_delete=models.CASCADE)
    # There are two PaymentSource items for each AccountTransferPayment
    # so this is FK not OneToOneField
    account_transfer_payment = models.ForeignKey(
        AccountTransferPayment, null=True, blank=True, on_delete=models.CASCADE
    )
    ipn_payment = models.OneToOneField(PayPalIPN, null=True, blank=True, on_delete=models.CASCADE)

    MODEL_MAP = {
        # Map of model class to FK attribute (above) for each payment source
        ManualPayment: "manual_payment",
        RefundPayment: "refund_payment",
        WriteOffDebt: "write_off_debt",
        AccountTransferPayment: "account_transfer_payment",
        PayPalIPN: "ipn_payment",
    }

    def save(self, *args, **kwargs):
        self._assert_one_source()
        super().save()

    @property
    def payment_type(self):
        if self.manual_payment_id is not None:
            return self.manual_payment.get_payment_type_display()
        elif self.refund_payment_id is not None:
            return "Refund " + self.refund_payment.get_payment_type_display()
        elif self.write_off_debt_id is not None:
            return "Write off debt"
        elif self.account_transfer_payment_id is not None:
            return "Account transfer"
        elif self.ipn_payment_id is not None:
            return "PayPal"
        else:
            raise ValueError(f"No related object for PaymentSource {self.id}")

    @property
    def model_source(self) -> PaymentModel | None:
        for att in self.MODEL_MAP.values():
            if getattr(self, f"{att}_id") is not None:
                return getattr(self, att)
        return None

    def _assert_one_source(self):
        attrs = [f"{a}_id" for a in self.MODEL_MAP.values()]
        if not [getattr(self, a) for a in attrs].count(None) == len(attrs) - 1:
            raise AssertionError("PaymentSource must have exactly one payment FK set")

    @classmethod
    def from_source_instance(cls, source_instance: PaymentModel):
        """
        Create a PaymentSource from a real payment model
        """
        source_cls = source_instance.__class__
        if source_cls not in cls.MODEL_MAP:
            raise AssertionError(f"Can't create PaymentSource for {source_cls}")
        attr_name_for_model = cls.MODEL_MAP[source_cls]
        return cls.objects.create(**{attr_name_for_model: source_instance})


def credit_account(amount: Decimal, to_account: BookingAccount, from_obj: PaymentModel | None):
    Payment.objects.create(
        amount=amount, account=to_account, source_instance=from_obj, processed_at=None, created_at=timezone.now()
    )
    process_all_payments()


def build_paypal_custom_field(account):
    return f"account:{account.id};"


def parse_paypal_custom_field(custom: str) -> BookingAccount | None:
    m = re.match(r"account:(\d+);", custom)
    if m is None:
        return None

    try:
        return BookingAccount.objects.get(id=int(m.groups()[0]))
    except BookingAccount.DoesNotExist:
        return None


@transaction.atomic()
def process_one_payment(payment: Payment):
    payment.account.receive_payment(payment.amount)
    payment.processed_at = timezone.now()
    # Payment uses NoEditMixin which disables save(), so do update()
    Payment.objects.filter(id=payment.id).update(processed_at=payment.processed_at)


# When processing payments, we need to alter the BookingAccount.total_received
# field, and may need to deal with concurrency, to avoid race conditions that
# would cause this field to have the wrong value.
#
# We arrange for updates to BookingAccount.total_received to be serialised
# using the function below.
#
# To support this, the Payment model keeps track of payments to be credited
# against an account. Any function that needs to transfer funds into an account
# uses 'cciw.bookings.models.send_payment', which creates Payment objects for
# later processing, rather than calling BookingAccount.receive_payment directly.


@transaction.atomic()
def process_all_payments():
    # Use select_for_update to serialize usages of this function.
    for payment in (
        Payment.objects.select_related(None)
        .select_for_update()
        .filter(processed_at__isnull=True)
        .order_by("created_at")
    ):
        process_one_payment(payment)

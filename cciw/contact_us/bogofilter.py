import logging
import subprocess

from django.conf import settings
from django.core.mail import EmailMessage
from django.db.models import TextChoices

logger = logging.getLogger(__name__)


class BogofilterStatus(TextChoices):
    HAM = "HAM", "Ham"
    SPAM = "SPAM", "Spam"
    UNSURE = "UNSURE", "Unsure"
    ERROR = "ERROR", "Error"
    UNCLASSIFIED = "UNCLASSIFIED", "Unclassified"


class BogofilterException(Exception):
    pass


def _bogofilter_command(args):
    return ["bogofilter", "-d", settings.BOGOFILTER_DIR] + args


def make_email_msg(from_email, subject, body, extra_headers=None) -> bytes:
    msg = EmailMessage(subject=subject, from_email=from_email, body=body, headers=extra_headers)
    return msg.message().as_bytes()


def mark_spam(msg_bytes: bytes):
    subprocess.run(_bogofilter_command(["-s"]), input=msg_bytes, check=True)


def mark_ham(msg_bytes):
    subprocess.run(_bogofilter_command(["-n"]), input=msg_bytes, check=True)


_STATUS_MAP = {
    "U": BogofilterStatus.UNSURE,
    "H": BogofilterStatus.HAM,
    "S": BogofilterStatus.SPAM,
}


def get_bogofilter_classification(msg_bytes) -> tuple[BogofilterStatus, float | None]:
    result = subprocess.run(_bogofilter_command(["-T"]), input=msg_bytes, capture_output=True)
    if result.returncode > 2:
        logger.error("Error running bogofilter: %r", result.stderr)
        return (BogofilterStatus.ERROR, None)
    status, score = result.stdout.decode("utf-8").strip().split()
    return (_STATUS_MAP[status], float(score))

from cciw.utils.tests.factories import Auto

from ..models import ContactType, Message


def create_message(message: str = Auto) -> Message:
    return Message.objects.create(
        subject=ContactType.WEBSITE,
        email="someemail@example.com",
        name="Some Person",
        message="This is an important message please read it" if message is Auto else message,
    )

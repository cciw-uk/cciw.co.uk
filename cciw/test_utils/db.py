from django.db.models import Model


def refresh[T: Model](obj: T) -> T:
    return obj.__class__.objects.get(id=obj.id)

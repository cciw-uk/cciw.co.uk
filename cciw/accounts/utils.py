from django.db import models
from django.db.transaction import atomic

from cciw.accounts.models import User


@atomic
def merge_model_instances(from_instances: list, to_instance: models.Model):
    if not from_instances:
        return
    for from_instance in from_instances:
        assert type(from_instance) is type(to_instance)
    model_cls = from_instances[0].__class__
    relations = [f for f in model_cls._meta.get_fields() if f.is_relation]
    many_to_many_fields = [f for f in relations if f.many_to_many]
    other_related_fields = [f for f in relations if not f.many_to_many]

    for from_instance in from_instances:
        for m2m in many_to_many_fields:
            if m2m.through._meta.auto_created is False:
                # This is a manually added `ManyToManyField` with a `through`
                # set to a manually created model. The FK on that model can be
                # used to fix this relationship, we don't need to do it here.
                continue
            relname = m2m.name
            related_objects = getattr(from_instance, relname)
            for obj in related_objects.all():
                getattr(from_instance, relname).remove(obj)
                getattr(to_instance, relname).add(obj)

        for related_field in other_related_fields:
            if related_field.one_to_many:
                relname = related_field.get_accessor_name()
                related_objects = getattr(from_instance, relname)
                for obj in related_objects.all():
                    field_name = related_field.field.name
                    setattr(obj, field_name, to_instance)
                    obj.save()
            elif related_field.one_to_one or related_field.many_to_one:
                relname = related_field.name
                related_object = getattr(from_instance, relname)
                primary_related_object = getattr(to_instance, relname)
                if primary_related_object is None:
                    setattr(to_instance, relname, related_object)
                    to_instance.save()
                elif related_field.one_to_one:
                    related_object.delete()

    for from_instance in from_instances:
        from_instance.delete()


def merge_users(from_user: User, to_user: User):
    merge_model_instances([from_user], to_user)

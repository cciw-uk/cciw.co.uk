from django.core.exceptions import ValidationError


class NoEditMixin:
    def clean(self):
        retval = super().clean()
        if self.id is not None:
            raise ValidationError(
                f"A {self.__class__._meta.verbose_name} record cannot be changed "
                "after being created. If an error was made, "
                "delete this record and create a new one. "
            )
        return retval

    def save(self, **kwargs):
        if self.id is not None:
            raise Exception(f"{self.__class__.__name__} cannot be edited after it has been saved to DB")
        else:
            return super().save(**kwargs)

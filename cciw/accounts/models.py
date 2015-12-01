from django.contrib.auth.models import AbstractUser


class User(AbstractUser):

    def __str__(self):
        return "{0} {1} <{2}>".format(self.first_name, self.last_name, self.email)

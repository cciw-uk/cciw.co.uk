import django.contrib.auth.models
import django.core.validators
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0006_require_contenttypes_0002"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.AutoField(verbose_name="ID", serialize=False, primary_key=True, auto_created=True)),
                ("password", models.CharField(verbose_name="password", max_length=128)),
                ("last_login", models.DateTimeField(verbose_name="last login", null=True, blank=True)),
                (
                    "is_superuser",
                    models.BooleanField(
                        verbose_name="superuser status",
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        default=False,
                    ),
                ),
                (
                    "username",
                    models.CharField(
                        verbose_name="username",
                        max_length=30,
                        help_text="Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.",
                        validators=[
                            django.core.validators.RegexValidator(
                                "^[\\w.@+-]+$",
                                "Enter a valid username. This value may contain only letters, numbers and @/./+/-/_ characters.",
                            )
                        ],
                        unique=True,
                        error_messages={"unique": "A user with that username already exists."},
                    ),
                ),
                ("first_name", models.CharField(verbose_name="first name", max_length=30, blank=True)),
                ("last_name", models.CharField(verbose_name="last name", max_length=30, blank=True)),
                ("email", models.EmailField(verbose_name="email address", max_length=254, blank=True)),
                (
                    "is_staff",
                    models.BooleanField(
                        verbose_name="staff status",
                        help_text="Designates whether the user can log into this admin site.",
                        default=False,
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        verbose_name="active",
                        help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.",
                        default=True,
                    ),
                ),
                ("date_joined", models.DateTimeField(verbose_name="date joined", default=django.utils.timezone.now)),
                (
                    "groups",
                    models.ManyToManyField(
                        verbose_name="groups",
                        blank=True,
                        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                        related_name="customtemp_user_set",
                        related_query_name="customtemp_user",
                        to="auth.Group",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        verbose_name="user permissions",
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="customtemp_user_set",
                        related_query_name="customtemp_user",
                        to="auth.Permission",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "users",
                "abstract": False,
                "verbose_name": "user",
            },
            managers=[
                ("objects", django.contrib.auth.models.UserManager()),
            ],
        ),
    ]

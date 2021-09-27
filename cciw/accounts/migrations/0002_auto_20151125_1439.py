from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_squashed_0006_auto_20150818_1728"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="groups",
            field=models.ManyToManyField(
                to="auth.Group",
                blank=True,
                verbose_name="groups",
                help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                related_query_name="user",
                related_name="user_set",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="user_permissions",
            field=models.ManyToManyField(
                to="auth.Permission",
                blank=True,
                verbose_name="user permissions",
                help_text="Specific permissions for this user.",
                related_query_name="user",
                related_name="user_set",
            ),
        ),
    ]

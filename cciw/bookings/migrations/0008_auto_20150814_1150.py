from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0007_fix_empty_values'),
    ]

    operations = [
        migrations.AlterField(
            model_name='booking',
            name='email',
            field=models.EmailField(max_length=254, blank=True),
        ),
        migrations.AlterField(
            model_name='bookingaccount',
            name='email',
            field=models.EmailField(max_length=254, blank=True, unique=True, null=True),
        ),
        migrations.AlterField(
            model_name='manualpayment',
            name='account',
            field=models.ForeignKey(to='bookings.BookingAccount', related_name='manual_payments', on_delete=models.CASCADE),
        ),
        migrations.AlterField(
            model_name='refundpayment',
            name='account',
            field=models.ForeignKey(to='bookings.BookingAccount', related_name='refund_payments', on_delete=models.CASCADE),
        ),
    ]

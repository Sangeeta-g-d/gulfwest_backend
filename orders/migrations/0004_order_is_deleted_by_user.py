# Generated by Django 5.2.1 on 2025-07-02 05:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_rename_payment_method_order_payment_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='is_deleted_by_user',
            field=models.BooleanField(default=False),
        ),
    ]

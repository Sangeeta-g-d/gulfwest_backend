# Generated by Django 5.2.1 on 2025-05-21 10:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0031_flashsale'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='flashsale',
            name='description',
        ),
        migrations.AddField(
            model_name='flashsale',
            name='tagline',
            field=models.CharField(blank=True, max_length=400, null=True),
        ),
    ]

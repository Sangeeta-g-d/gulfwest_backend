# Generated by Django 5.2.1 on 2025-07-10 06:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0052_categories_is_enabled'),
    ]

    operations = [
        migrations.AddField(
            model_name='onboardingimage',
            name='sub_title',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='onboardingimage',
            name='title',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]

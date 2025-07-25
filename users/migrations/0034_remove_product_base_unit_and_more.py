# Generated by Django 5.2.1 on 2025-05-31 05:08

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0033_flashsale_background_image'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='base_unit',
        ),
        migrations.RemoveField(
            model_name='product',
            name='discount_price',
        ),
        migrations.RemoveField(
            model_name='product',
            name='price',
        ),
        migrations.RemoveField(
            model_name='product',
            name='quantity_in_base_unit',
        ),
        migrations.RemoveField(
            model_name='product',
            name='selling_quantity',
        ),
        migrations.RemoveField(
            model_name='product',
            name='selling_unit',
        ),
        migrations.RemoveField(
            model_name='product',
            name='status',
        ),
        migrations.RemoveField(
            model_name='product',
            name='threshold_quantity',
        ),
        migrations.CreateModel(
            name='ProductVariant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('selling_quantity', models.DecimalField(decimal_places=2, max_digits=10)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('discount_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('quantity_in_base_unit', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('threshold_quantity', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('status', models.CharField(choices=[('in', 'In Stock'), ('running_out', 'Running Out'), ('out_of_stock', 'Out of Stock')], default='in', max_length=20)),
                ('base_unit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='variant_base_units', to='users.unit')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='variants', to='users.product')),
                ('selling_unit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.unit')),
            ],
        ),
    ]

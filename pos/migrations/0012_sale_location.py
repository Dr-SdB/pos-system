from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0011_sale_flat_discount'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='location',
            field=models.CharField(
                choices=[('Loja', 'Loja'), ('Online', 'Online')],
                default='Loja',
                max_length=20,
            ),
        ),
    ]

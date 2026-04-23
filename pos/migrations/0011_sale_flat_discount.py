from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0010_userprofile_must_change_password'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='flat_discount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
    ]

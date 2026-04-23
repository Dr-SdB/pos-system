from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0012_sale_location'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='temp_password',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
    ]

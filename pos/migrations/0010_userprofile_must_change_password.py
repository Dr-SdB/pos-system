from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0009_tenant_icon'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='must_change_password',
            field=models.BooleanField(default=False),
        ),
    ]

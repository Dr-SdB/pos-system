from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0013_userprofile_temp_password'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stockadjustment',
            name='reason',
            field=models.CharField(
                choices=[
                    ('Dano', 'Dano'),
                    ('Perda', 'Perda'),
                    ('Roubo', 'Roubo'),
                    ('Teste', 'Teste'),
                    ('Outro', 'Outro'),
                    ('Reposição', 'Reposição'),
                    ('Reposto', 'Reposto'),
                ],
                max_length=20,
            ),
        ),
    ]

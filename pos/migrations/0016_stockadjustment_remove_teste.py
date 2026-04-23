from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0015_stockadjustment_add_anulado'),
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
                    ('Outro', 'Outro'),
                    ('Reposição', 'Reposição'),
                    ('Reposto', 'Reposto'),
                    ('Anulado', 'Anulado'),
                ],
                max_length=20,
            ),
        ),
    ]

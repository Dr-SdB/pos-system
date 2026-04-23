from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='payment_method',
            field=models.CharField(
                choices=[
                    ('Dinheiro', 'Dinheiro'),
                    ('E-Mola', 'E-Mola'),
                    ('Cartao', 'Cartão'),
                    ('Transferencia', 'Transferência'),
                ],
                default='Dinheiro',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='sale',
            name='amount_paid',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='sale',
            name='change_given',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
    ]

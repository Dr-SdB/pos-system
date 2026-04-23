from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0002_sale_payment_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='customer_name',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='sale',
            name='attendant',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='sale',
            name='notes',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='sale',
            name='payment_method',
            field=models.CharField(
                choices=[
                    ('Dinheiro', 'Dinheiro'),
                    ('M-Pesa', 'M-Pesa'),
                    ('E-Mola', 'E-Mola'),
                    ('eMola', 'eMola'),
                    ('Cartao', 'Cartão'),
                    ('Transferencia', 'Transferência'),
                    ('POS', 'POS'),
                ],
                default='Dinheiro',
                max_length=20,
            ),
        ),
    ]

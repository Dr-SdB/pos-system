from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0003_sale_customer_attendant'),
    ]

    operations = [
        migrations.CreateModel(
            name='StockAdjustment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField()),
                ('reason', models.CharField(choices=[('Dano','Dano'),('Perda','Perda'),('Roubo','Roubo'),('Teste','Teste'),('Outro','Outro'),('Reposição','Reposição')], max_length=20)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('product_variant', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='adjustments', to='pos.productvariant')),
            ],
        ),
    ]

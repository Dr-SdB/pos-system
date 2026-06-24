import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0017_add_performance_indexes'),
    ]

    operations = [
        migrations.CreateModel(
            name='CatalogueChangeLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('variant_sku', models.CharField(max_length=80)),
                ('product_name', models.CharField(max_length=255)),
                ('action', models.CharField(choices=[('Preço alterado', 'Preço alterado'), ('Stock definido', 'Stock definido'), ('Artigo eliminado', 'Artigo eliminado'), ('Nome alterado', 'Nome alterado'), ('Categoria alterada', 'Categoria alterada')], max_length=30)),
                ('old_value', models.CharField(blank=True, max_length=255)),
                ('new_value', models.CharField(blank=True, max_length=255)),
                ('changed_by', models.CharField(max_length=150)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('product_variant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='catalogue_logs', to='pos.productvariant')),
                ('tenant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='pos.tenant')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]

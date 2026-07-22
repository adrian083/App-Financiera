from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('presupuesto', '0011_configuracionusuario_avatar'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracionusuario',
            name='foto_perfil',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='perfiles/',
                verbose_name='Foto de perfil',
            ),
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('presupuesto', '0010_remove_configuracionusuario_foto_perfil'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracionusuario',
            name='avatar',
            field=models.CharField(default='inicial', max_length=30, verbose_name='Avatar de perfil'),
        ),
    ]

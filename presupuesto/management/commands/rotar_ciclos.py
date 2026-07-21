from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from presupuesto.services import verificar_cierre_pendiente, cerrar_ciclo
from presupuesto.models import ConfiguracionUsuario


class Command(BaseCommand):
    help = 'Rota automáticamente los ciclos que han pasado el plazo de tolerancia'

    def handle(self, *args, **options):
        self.stdout.write('Verificando ciclos que requieren rotación automática...')
        
        usuarios_rotados = 0
        usuarios_sin_config = 0
        
        for user in User.objects.filter(is_active=True):
            config = ConfiguracionUsuario.obtener(user)
            if not config.configurado:
                usuarios_sin_config += 1
                continue
            
            ciclo_pendiente = verificar_cierre_pendiente(user)
            if ciclo_pendiente:
                try:
                    # Cerrar ciclo actual y crear nuevo pendiente
                    nuevo_ciclo = cerrar_ciclo(
                        user, 
                        ciclo_pendiente, 
                        config.salario_base
                    )
                    usuarios_rotados += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ Ciclo rotado para {user.username}: '
                            f'{ciclo_pendiente.etiqueta} → {nuevo_ciclo.etiqueta}'
                        )
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'✗ Error rotando ciclo para {user.username}: {str(e)}'
                        )
                    )
        
        self.stdout.write(self.style.SUCCESS(
            f'\nResumen: {usuarios_rotados} usuarios rotados, '
            f'{usuarios_sin_config} sin configuración'
        ))

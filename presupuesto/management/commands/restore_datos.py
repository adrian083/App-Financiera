"""Management command para restaurar datos desde un backup JSON."""
import json
from datetime import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from presupuesto.models import ConfiguracionUsuario, Categoria, Movimiento, CicloMensual, GastoFijoPlantilla, EventoCalendario
from ahorros.models import FondoAhorro, Inversion, MetaAhorro, MovimientoPatrimonio
from decimal import Decimal


class Command(BaseCommand):
    help = 'Restaura datos desde un archivo JSON de backup'

    def add_arguments(self, parser):
        parser.add_argument('--archivo', type=str, help='Archivo JSON de backup a restaurar')
        parser.add_argument('--usuario', type=str, help='Username del usuario destino')

    def handle(self, *args, **options):
        archivo = options.get('archivo')
        if not archivo:
            self.stdout.write(self.style.ERROR('Debe especificar un archivo con --archivo'))
            return

        username = options.get('usuario')
        if not username:
            self.stdout.write(self.style.ERROR('Debe especificar un usuario destino con --usuario'))
            return

        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                datos = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Archivo {archivo} no encontrado'))
            return
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR(f'Archivo {archivo} no es un JSON válido'))
            return

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Usuario {username} no encontrado'))
            return

        self.stdout.write(f'Restaurando backup del {datos["backup_fecha"]}')
        
        # Restaurar configuración
        self.restore_configuracion(user, datos.get('configuracion'))
        
        # Restaurar categorías
        self.restore_categorias(user, datos.get('categorias', []))
        
        # Restaurar gastos fijos
        self.restore_gastos_fijos(user, datos.get('gastos_fijos', []))
        
        # Restaurar eventos de calendario
        self.restore_eventos(user, datos.get('eventos_calendario', []))
        
        # Restaurar metas de ahorro
        self.restore_metas_ahorro(user, datos.get('metas_ahorro', []))
        
        # Nota: No restauramos movimientos, ciclos, inversiones ni movimientos de patrimonio
        # porque dependen de relaciones complejas que podrían causar inconsistencias
        
        self.stdout.write(self.style.SUCCESS('Backup restaurado exitosamente'))
        self.stdout.write(self.style.WARNING('Nota: Movimientos, ciclos e inversiones no fueron restaurados para evitar inconsistencias'))

    def restore_configuracion(self, user, config_data):
        if not config_data:
            return
        
        config, created = ConfiguracionUsuario.objects.get_or_create(
            usuario=user,
            defaults={
                'salario_base': Decimal(config_data['salario_base']),
                'dia_corte': config_data['dia_corte'],
                'dias_plazo_tolerancia': config_data['dias_plazo_tolerancia'],
                'moneda': config_data['moneda'],
                'configurado': config_data['configurado'],
                'ha_visto_tutorial': config_data['ha_visto_tutorial'],
            }
        )
        
        if not created:
            config.salario_base = Decimal(config_data['salario_base'])
            config.dia_corte = config_data['dia_corte']
            config.dias_plazo_tolerancia = config_data['dias_plazo_tolerancia']
            config.moneda = config_data['moneda']
            config.configurado = config_data['configurado']
            config.ha_visto_tutorial = config_data['ha_visto_tutorial']
            config.save()
        
        self.stdout.write(f'  ✓ Configuración restaurada')

    def restore_categorias(self, user, categorias_data):
        for cat_data in categorias_data:
            Categoria.objects.get_or_create(
                usuario=user,
                nombre=cat_data['nombre'],
                defaults={
                    'color': cat_data['color'],
                    'tipo': cat_data['tipo'],
                    'presupuesto_mensual': Decimal(cat_data['presupuesto_mensual']),
                }
            )
        self.stdout.write(f'  ✓ {len(categorias_data)} categorías restauradas')

    def restore_gastos_fijos(self, user, gastos_data):
        for gasto_data in gastos_data:
            categoria = None
            if gasto_data.get('categoria_nombre'):
                try:
                    categoria = Categoria.objects.get(usuario=user, nombre=gasto_data['categoria_nombre'])
                except Categoria.DoesNotExist:
                    pass
            
            GastoFijoPlantilla.objects.get_or_create(
                usuario=user,
                descripcion=gasto_data['descripcion'],
                defaults={
                    'monto': Decimal(gasto_data['monto']),
                    'categoria': categoria,
                    'frecuencia': gasto_data['frecuencia'],
                    'activa': gasto_data['activa'],
                }
            )
        self.stdout.write(f'  ✓ {len(gastos_data)} gastos fijos restaurados')

    def restore_eventos(self, user, eventos_data):
        for evento_data in eventos_data:
            EventoCalendario.objects.get_or_create(
                usuario=user,
                titulo=evento_data['titulo'],
                fecha=datetime.fromisoformat(evento_data['fecha']).date(),
                defaults={
                    'descripcion': evento_data.get('descripcion', ''),
                    'tipo': evento_data['tipo'],
                    'monto': Decimal(evento_data['monto']) if evento_data.get('monto') else None,
                    'repetir_anualmente': evento_data['repetir_anualmente'],
                    'completado': evento_data['completado'],
                }
            )
        self.stdout.write(f'  ✓ {len(eventos_data)} eventos restaurados')

    def restore_metas_ahorro(self, user, metas_data):
        for meta_data in metas_data:
            MetaAhorro.objects.get_or_create(
                usuario=user,
                nombre=meta_data['nombre'],
                defaults={
                    'objetivo': Decimal(meta_data['objetivo']),
                    'ahorrado': Decimal(meta_data['ahorrado']),
                    'icono': meta_data['icono'],
                    'fecha_objetivo': datetime.fromisoformat(meta_data['fecha_objetivo']).date() if meta_data.get('fecha_objetivo') else None,
                }
            )
        self.stdout.write(f'  ✓ {len(metas_data)} metas de ahorro restauradas')

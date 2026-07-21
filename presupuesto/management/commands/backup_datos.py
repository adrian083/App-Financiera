"""Management command para crear backup de datos del usuario."""
import json
from datetime import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from presupuesto.models import ConfiguracionUsuario, Categoria, Movimiento, CicloMensual, GastoFijoPlantilla, EventoCalendario
from ahorros.models import FondoAhorro, Inversion, MetaAhorro, MovimientoPatrimonio


class Command(BaseCommand):
    help = 'Crea un backup de todos los datos del usuario en formato JSON'

    def add_arguments(self, parser):
        parser.add_argument('--usuario', type=str, help='Username del usuario a hacer backup')
        parser.add_argument('--archivo', type=str, help='Nombre del archivo de backup')

    def handle(self, *args, **options):
        username = options.get('usuario')
        if not username:
            self.stdout.write(self.style.ERROR('Debe especificar un usuario con --usuario'))
            return

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Usuario {username} no encontrado'))
            return

        # Recopilar todos los datos
        datos = {
            'backup_fecha': datetime.now().isoformat(),
            'usuario': {
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'date_joined': user.date_joined.isoformat(),
            },
            'configuracion': self.serialize_configuracion(user),
            'categorias': self.serialize_categorias(user),
            'movimientos': self.serialize_movimientos(user),
            'ciclos': self.serialize_ciclos(user),
            'gastos_fijos': self.serialize_gastos_fijos(user),
            'eventos_calendario': self.serialize_eventos(user),
            'fondo_ahorro': self.serialize_fondo_ahorro(user),
            'inversiones': self.serialize_inversiones(user),
            'metas_ahorro': self.serialize_metas_ahorro(user),
            'movimientos_patrimonio': self.serialize_movimientos_patrimonio(user),
        }

        # Guardar en archivo
        filename = options.get('archivo') or f'backup_{username}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS(f'Backup creado exitosamente: {filename}'))

    def serialize_configuracion(self, user):
        try:
            config = ConfiguracionUsuario.objects.get(usuario=user)
            return {
                'salario_base': str(config.salario_base),
                'dia_corte': config.dia_corte,
                'dias_plazo_tolerancia': config.dias_plazo_tolerancia,
                'moneda': config.moneda,
                'configurado': config.configurado,
                'ha_visto_tutorial': config.ha_visto_tutorial,
            }
        except ConfiguracionUsuario.DoesNotExist:
            return None

    def serialize_categorias(self, user):
        return list(Categoria.objects.filter(usuario=user).values(
            'nombre', 'color', 'tipo', 'presupuesto_mensual'
        ))

    def serialize_movimientos(self, user):
        movimientos = []
        for mov in Movimiento.objects.filter(usuario=user):
            movimientos.append({
                'tipo': mov.tipo,
                'monto': str(mov.monto),
                'descripcion': mov.descripcion,
                'categoria_nombre': mov.categoria.nombre if mov.categoria else None,
                'es_gasto_fijo': mov.es_gasto_fijo,
                'pagado': mov.pagado,
                'fecha_registro': mov.fecha_registro.isoformat(),
                'fecha_vencimiento': mov.fecha_vencimiento.isoformat() if mov.fecha_vencimiento else None,
            })
        return movimientos

    def serialize_ciclos(self, user):
        ciclos = []
        for ciclo in CicloMensual.objects.filter(usuario=user):
            ciclos.append({
                'fecha_inicio': ciclo.fecha_inicio.isoformat(),
                'fecha_cierre': ciclo.fecha_cierre.isoformat() if ciclo.fecha_cierre else None,
                'salario_ciclo': str(ciclo.salario_ciclo),
                'estado': ciclo.estado,
                'sobrante_transferido': str(ciclo.sobrante_transferido),
            })
        return ciclos

    def serialize_gastos_fijos(self, user):
        gastos = []
        for gasto in GastoFijoPlantilla.objects.filter(usuario=user):
            gastos.append({
                'descripcion': gasto.descripcion,
                'monto': str(gasto.monto),
                'categoria_nombre': gasto.categoria.nombre if gasto.categoria else None,
                'frecuencia': gasto.frecuencia,
                'activa': gasto.activa,
                'fecha_ultima_aplicacion': gasto.fecha_ultima_aplicacion.isoformat() if gasto.fecha_ultima_aplicacion else None,
            })
        return gastos

    def serialize_eventos(self, user):
        eventos = []
        for evento in EventoCalendario.objects.filter(usuario=user):
            eventos.append({
                'titulo': evento.titulo,
                'descripcion': evento.descripcion,
                'fecha': evento.fecha.isoformat(),
                'tipo': evento.tipo,
                'monto': str(evento.monto) if evento.monto else None,
                'repetir_anualmente': evento.repetir_anualmente,
                'completado': evento.completado,
            })
        return eventos

    def serialize_fondo_ahorro(self, user):
        try:
            fondo = FondoAhorro.objects.get(usuario=user)
            return {
                'saldo_disponible': str(fondo.saldo_disponible),
            }
        except FondoAhorro.DoesNotExist:
            return None

    def serialize_inversiones(self, user):
        inversiones = []
        for inv in Inversion.objects.filter(usuario=user):
            inversiones.append({
                'nombre': inv.nombre,
                'monto_inicial': str(inv.monto_inicial),
                'monto_final': str(inv.monto_final) if inv.monto_final else None,
                'rendimiento_esperado': str(inv.rendimiento_esperado) if inv.rendimiento_esperado else None,
                'tipo_activo': inv.tipo_activo,
                'fecha_inicio': inv.fecha_inicio.isoformat() if inv.fecha_inicio else None,
                'fecha_vencimiento': inv.fecha_vencimiento.isoformat() if inv.fecha_vencimiento else None,
                'estado': inv.estado,
                'notas': inv.notas,
            })
        return inversiones

    def serialize_metas_ahorro(self, user):
        metas = []
        for meta in MetaAhorro.objects.filter(usuario=user):
            metas.append({
                'nombre': meta.nombre,
                'objetivo': str(meta.objetivo),
                'ahorrado': str(meta.ahorrado),
                'icono': meta.icono,
                'fecha_objetivo': meta.fecha_objetivo.isoformat() if meta.fecha_objetivo else None,
            })
        return metas

    def serialize_movimientos_patrimonio(self, user):
        movimientos = []
        for mov in MovimientoPatrimonio.objects.filter(usuario=user):
            movimientos.append({
                'tipo': mov.tipo,
                'monto': str(mov.monto),
                'descripcion': mov.descripcion,
                'fecha': mov.fecha.isoformat(),
            })
        return movimientos

"""Servicios de negocio del módulo de presupuesto."""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from core.utils.fechas import (
    debe_cerrar_ciclo,
    esta_en_plazo_confirmacion,
    fecha_inicio_plazo_confirmacion,
    fecha_limite_plazo_confirmacion,
    paso_plazo_confirmacion,
)
from presupuesto.models import (
    CicloMensual,
    ConfiguracionUsuario,
    GastoFijoPlantilla,
    Movimiento,
)


def debe_aplicar_gasto_fijo(plantilla: GastoFijoPlantilla, fecha_ciclo: date) -> bool:
    """Determina si un gasto fijo debe aplicarse en el ciclo actual según su frecuencia."""
    if not plantilla.fecha_ultima_aplicacion:
        return True  # Primera vez, siempre aplicar
    
    meses_frecuencia = {
        GastoFijoPlantilla.MENSUAL: 1,
        GastoFijoPlantilla.BIMENSUAL: 2,
        GastoFijoPlantilla.TRIMESTRAL: 3,
        GastoFijoPlantilla.SEMESTRAL: 6,
        GastoFijoPlantilla.ANUAL: 12,
    }
    
    meses = meses_frecuencia.get(plantilla.frecuencia, 1)
    
    # Calcular fecha de próxima aplicación esperada
    ultima = plantilla.fecha_ultima_aplicacion
    # Avanzar meses según frecuencia
    year = ultima.year
    month = ultima.month + meses
    while month > 12:
        month -= 12
        year += 1
    
    # Ajustar día si el mes no tiene ese día
    import calendar
    max_day = calendar.monthrange(year, month)[1]
    day = min(ultima.day, max_day)
    
    proxima_aplicacion = date(year, month, day)
    
    return fecha_ciclo >= proxima_aplicacion


def copiar_gastos_fijos(usuario, ciclo: CicloMensual):
    """Clona plantillas de gastos fijos al nuevo ciclo respetando la frecuencia."""
    for plantilla in GastoFijoPlantilla.objects.filter(usuario=usuario, activa=True):
        if debe_aplicar_gasto_fijo(plantilla, ciclo.fecha_inicio):
            Movimiento.objects.create(
                usuario=usuario,
                ciclo=ciclo,
                tipo=Movimiento.GASTO,
                monto=plantilla.monto,
                descripcion=plantilla.descripcion,
                categoria=plantilla.categoria,
                es_gasto_fijo=True,
                plantilla_origen=plantilla,
            )
            # Actualizar fecha de última aplicación
            plantilla.fecha_ultima_aplicacion = ciclo.fecha_inicio
            plantilla.save(update_fields=['fecha_ultima_aplicacion'])


def crear_nuevo_ciclo(
    usuario,
    salario: Decimal,
    dia_corte: int,
    pendiente: bool = False,
) -> CicloMensual:
    estado = CicloMensual.PENDIENTE if pendiente else CicloMensual.ACTIVO
    ciclo = CicloMensual.crear_desde_fecha(
        usuario, timezone.now().date(), salario, dia_corte, estado=estado,
    )
    copiar_gastos_fijos(usuario, ciclo)
    return ciclo


def confirmar_ciclo_pendiente(ciclo: CicloMensual) -> CicloMensual:
    ciclo.estado = CicloMensual.ACTIVO
    ciclo.save(update_fields=['estado'])
    return ciclo


@transaction.atomic
def cerrar_ciclo(usuario, ciclo: CicloMensual, nuevo_salario: Decimal) -> CicloMensual:
    from ahorros.services import registrar_entrada_sobrante

    sobrante = ciclo.calcular_sobrante()
    if sobrante > 0:
        registrar_entrada_sobrante(usuario, ciclo, sobrante)
        ciclo.sobrante_transferido = sobrante

    ciclo.estado = CicloMensual.CERRADO
    ciclo.fecha_cierre = timezone.now()
    ciclo.save()

    config = ConfiguracionUsuario.obtener(usuario)
    config.salario_base = nuevo_salario
    config.save()

    return crear_nuevo_ciclo(usuario, nuevo_salario, config.dia_corte, pendiente=True)


def verificar_cierre_pendiente(usuario) -> CicloMensual | None:
    """Devuelve el ciclo activo que ya superó el plazo de tolerancia para confirmación."""
    ciclo = CicloMensual.obtener_activo(usuario)
    if not ciclo:
        return None
    config = ConfiguracionUsuario.obtener(usuario)
    if paso_plazo_confirmacion(ciclo.fecha_fin, config.dias_plazo_tolerancia):
        return ciclo
    return None


def obtener_ciclo_en_plazo_confirmacion(usuario) -> CicloMensual | None:
    ciclo = CicloMensual.obtener_activo(usuario)
    if not ciclo:
        return None
    config = ConfiguracionUsuario.obtener(usuario)
    if esta_en_plazo_confirmacion(ciclo.fecha_fin, config.dias_plazo_tolerancia):
        return ciclo
    return None


def get_fechas_plazo_confirmacion(ciclo: CicloMensual, dias_plazo_tolerancia: int) -> tuple[date, date]:
    inicio = fecha_inicio_plazo_confirmacion(ciclo.fecha_fin)
    limite = fecha_limite_plazo_confirmacion(ciclo.fecha_fin, dias_plazo_tolerancia)
    return inicio, limite


def asegurar_ciclo_activo(usuario) -> CicloMensual | None:
    config = ConfiguracionUsuario.obtener(usuario)
    if not config.configurado:
        return None
    pendiente = CicloMensual.obtener_pendiente(usuario)
    if pendiente:
        return pendiente
    ciclo = CicloMensual.obtener_activo(usuario)
    if not ciclo:
        return crear_nuevo_ciclo(usuario, config.salario_base, config.dia_corte)
    return ciclo

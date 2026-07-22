"""Generación del centro de notificaciones.

Construye una lista de notificaciones "en vivo" a partir del estado financiero
del usuario: pagos por vencer o vencidos, eventos próximos del calendario, plazo
de confirmación del ciclo y alertas de saldo bajo. No persiste nada en la base de
datos; se recalcula en cada request para el usuario autenticado.
"""
from __future__ import annotations

from datetime import date, timedelta

from core.utils.moneda import formato_cop
from presupuesto.models import (
    CicloMensual,
    ConfiguracionUsuario,
    EventoCalendario,
    Movimiento,
)

# Ventana (en días) para considerar un pago/evento como "próximo".
DIAS_PROXIMO = 7
# Umbral relativo para avisar de saldo bajo (10% de los ingresos del ciclo).
UMBRAL_SALDO_BAJO = 0.10


def _dias_texto(dias: int) -> str:
    if dias < 0:
        n = abs(dias)
        return 'vencido hace 1 día' if n == 1 else f'vencido hace {n} días'
    if dias == 0:
        return 'vence hoy'
    if dias == 1:
        return 'vence mañana'
    return f'vence en {dias} días'


def construir_notificaciones(usuario) -> list[dict]:
    """Devuelve las notificaciones ordenadas por prioridad para el usuario."""
    hoy = date.today()
    notifs: list[dict] = []

    try:
        config = ConfiguracionUsuario.obtener(usuario)
    except Exception:
        config = None

    if not config or not config.configurado:
        return notifs

    ciclo = CicloMensual.obtener_activo(usuario)

    # 1) Pagos (movimientos) no pagados con fecha de vencimiento cercana o pasada.
    if ciclo:
        pendientes = (
            Movimiento.objects.filter(
                usuario=usuario,
                ciclo=ciclo,
                tipo=Movimiento.GASTO,
                pagado=False,
                fecha_vencimiento__isnull=False,
            )
            .order_by('fecha_vencimiento')
        )
        for mov in pendientes:
            dias = (mov.fecha_vencimiento - hoy).days
            if dias > DIAS_PROXIMO:
                continue
            vencido = dias < 0
            notifs.append({
                'tipo': 'pago',
                'nivel': 'alerta' if vencido else 'aviso',
                'icono': 'fa-file-invoice-dollar',
                'titulo': mov.descripcion,
                'detalle': f'{formato_cop(mov.monto)} · {_dias_texto(dias)}',
                'fecha': mov.fecha_vencimiento,
                'orden': dias,
            })

    # 2) Eventos del calendario próximos (pagos / recordatorios sin completar).
    eventos = EventoCalendario.objects.filter(
        usuario=usuario,
        completado=False,
        fecha__gte=hoy,
        fecha__lte=hoy + timedelta(days=DIAS_PROXIMO),
    ).order_by('fecha')
    for ev in eventos:
        dias = (ev.fecha - hoy).days
        detalle = _dias_texto(dias)
        if ev.monto:
            detalle = f'{formato_cop(ev.monto)} · {detalle}'
        notifs.append({
            'tipo': 'evento',
            'nivel': 'aviso',
            'icono': 'fa-calendar-day' if ev.tipo == EventoCalendario.PAGO else 'fa-bell',
            'titulo': ev.titulo,
            'detalle': detalle,
            'fecha': ev.fecha,
            'orden': dias,
        })

    # 3) Plazo de confirmación del ciclo (cierre pendiente).
    if ciclo:
        limite = ciclo.fecha_fin + timedelta(days=1 + config.dias_plazo_tolerancia)
        if hoy > ciclo.fecha_fin:
            dias_para_limite = (limite - hoy).days
            notifs.append({
                'tipo': 'ciclo',
                'nivel': 'alerta' if dias_para_limite < 0 else 'aviso',
                'icono': 'fa-rotate',
                'titulo': 'Confirma el cierre de tu ciclo',
                'detalle': (
                    'El plazo de confirmación ya venció'
                    if dias_para_limite < 0
                    else f'Tienes {max(dias_para_limite, 0)} día(s) para confirmar'
                ),
                'fecha': limite,
                'orden': -1000,  # máxima prioridad
            })

    # 4) Saldo bajo respecto a los ingresos del ciclo.
    if ciclo:
        ingresos = ciclo.total_ingresos()
        saldo = ciclo.saldo_disponible()
        if ingresos > 0 and saldo <= (ingresos * UMBRAL_SALDO_BAJO):
            notifs.append({
                'tipo': 'saldo',
                'nivel': 'alerta' if saldo <= 0 else 'aviso',
                'icono': 'fa-wallet',
                'titulo': 'Saldo disponible bajo',
                'detalle': f'Te queda {formato_cop(saldo)} este ciclo',
                'fecha': hoy,
                'orden': -500,
            })

    # Ordenar: primero lo más urgente (orden menor), luego por fecha.
    notifs.sort(key=lambda n: (n['orden'], n['fecha']))
    return notifs

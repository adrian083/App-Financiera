"""Utilidades para ciclos financieros con día de corte parametrizable."""
import calendar
from datetime import date, timedelta


MESES_ES = [
    'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
    'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic',
]


def ultimo_dia_mes(anio: int, mes: int) -> int:
    return calendar.monthrange(anio, mes)[1]


def dia_corte_efectivo(anio: int, mes: int, dia_corte: int) -> int:
    """Adapta el día de corte a meses cortos (ej. febrero → 28/29)."""
    return min(dia_corte, ultimo_dia_mes(anio, mes))


def fecha_corte(anio: int, mes: int, dia_corte: int) -> date:
    dia = dia_corte_efectivo(anio, mes, dia_corte)
    return date(anio, mes, dia)


def inicio_ciclo_para_fecha(fecha: date, dia_corte: int) -> date:
    """Devuelve la fecha de inicio del ciclo que contiene `fecha`."""
    dia_ef = dia_corte_efectivo(fecha.year, fecha.month, dia_corte)
    if fecha.day >= dia_ef:
        return date(fecha.year, fecha.month, dia_ef)
    mes_anterior = fecha.month - 1 if fecha.month > 1 else 12
    anio_anterior = fecha.year if fecha.month > 1 else fecha.year - 1
    dia_ef_ant = dia_corte_efectivo(anio_anterior, mes_anterior, dia_corte)
    return date(anio_anterior, mes_anterior, dia_ef_ant)


def fin_ciclo(inicio: date, dia_corte: int) -> date:
    """Fin del ciclo: día anterior al siguiente corte."""
    if inicio.month == 12:
        anio_sig, mes_sig = inicio.year + 1, 1
    else:
        anio_sig, mes_sig = inicio.year, inicio.month + 1
    siguiente_corte = fecha_corte(anio_sig, mes_sig, dia_corte)
    return siguiente_corte - timedelta(days=1)


def etiqueta_ciclo(inicio: date, fin: date) -> str:
    anio = fin.year if fin.year != inicio.year else inicio.year
    if fin.year != inicio.year:
        return (
            f"{inicio.day} {MESES_ES[inicio.month - 1]} {inicio.year} - "
            f"{fin.day} {MESES_ES[fin.month - 1]} {fin.year}"
        )
    return f"{inicio.day} {MESES_ES[inicio.month - 1]} - {fin.day} {MESES_ES[fin.month - 1]} {anio}"


def debe_cerrar_ciclo(fecha_fin: date, hoy: date | None = None) -> bool:
    """True si ya pasó el fin del ciclo (nuevo corte debe iniciar)."""
    hoy = hoy or date.today()
    return hoy > fecha_fin


def fecha_inicio_plazo_confirmacion(fecha_fin: date) -> date:
    """Fecha estimada de pago: el día siguiente al fin del ciclo."""
    return fecha_fin + timedelta(days=1)


def fecha_limite_plazo_confirmacion(fecha_fin: date, dias_plazo_tolerancia: int) -> date:
    """Último día válido para confirmar el pago del ciclo."""
    return fecha_inicio_plazo_confirmacion(fecha_fin) + timedelta(days=dias_plazo_tolerancia)


def esta_en_plazo_confirmacion(fecha_fin: date, dias_plazo_tolerancia: int, hoy: date | None = None) -> bool:
    hoy = hoy or date.today()
    inicio = fecha_inicio_plazo_confirmacion(fecha_fin)
    limite = fecha_limite_plazo_confirmacion(fecha_fin, dias_plazo_tolerancia)
    return inicio <= hoy <= limite


def paso_plazo_confirmacion(fecha_fin: date, dias_plazo_tolerancia: int, hoy: date | None = None) -> bool:
    hoy = hoy or date.today()
    limite = fecha_limite_plazo_confirmacion(fecha_fin, dias_plazo_tolerancia)
    return hoy > limite

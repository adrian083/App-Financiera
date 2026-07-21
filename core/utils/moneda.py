"""Formateo de Pesos Colombianos (COP)."""
from decimal import Decimal, InvalidOperation


def parse_cop(valor: str | int | float | Decimal | None) -> Decimal:
    """Convierte '$ 1.200.000' o '1200000' a Decimal."""
    if valor is None or valor == '':
        return Decimal('0')
    if isinstance(valor, Decimal):
        return valor.quantize(Decimal('1'))
    if isinstance(valor, (int, float)):
        return Decimal(str(valor)).quantize(Decimal('1'))
    limpio = str(valor).replace('$', '').replace('.', '').replace(',', '').strip()
    if not limpio:
        return Decimal('0')
    try:
        return Decimal(limpio).quantize(Decimal('1'))
    except InvalidOperation:
        return Decimal('0')


def formato_cop(monto) -> str:
    """Formatea un monto usando la moneda activa del usuario (solo símbolo).

    Los montos no se convierten: se muestra el mismo valor con el símbolo y el
    separador de miles de la moneda seleccionada. El nombre se conserva por
    compatibilidad con las plantillas existentes que usan ``|cop``.
    """
    from core.currency import get_active_info

    info = get_active_info()
    if monto is None:
        monto = Decimal('0')
    if not isinstance(monto, Decimal):
        monto = Decimal(str(monto))
    monto = monto.quantize(Decimal('1'))
    negativo = monto < 0
    entero = abs(int(monto))
    texto = f'{entero:,}'.replace(',', info['sep_miles'])
    simbolo = info['simbolo']
    prefijo = f'-{simbolo} ' if negativo else f'{simbolo} '
    return f'{prefijo}{texto}'

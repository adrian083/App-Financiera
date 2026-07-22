"""Formateo de Pesos Colombianos (COP)."""
from decimal import Decimal, InvalidOperation


def parse_cop(valor: str | int | float | Decimal | None) -> Decimal:
    """Convierte '$ 1.200.000' o '1200000' a Decimal."""
    try:
        if valor is None or valor == '':
            return Decimal('0')
        if isinstance(valor, Decimal):
            return valor.quantize(Decimal('1'))
        if isinstance(valor, (int, float)):
            return Decimal(str(valor)).quantize(Decimal('1'))
        limpio = str(valor).replace('$', '').replace('.', '').replace(',', '').strip()
        if not limpio:
            return Decimal('0')
        return Decimal(limpio).quantize(Decimal('1'))
    except (InvalidOperation, ValueError, TypeError, AttributeError):
        return Decimal('0')


def formato_cop(monto) -> str:
    """Formatea un monto usando la moneda activa del usuario (solo símbolo).

    Los montos no se convierten: se muestra el mismo valor con el símbolo y el
    separador de miles de la moneda seleccionada. El nombre se conserva por
    compatibilidad con las plantillas existentes que usan ``|cop``.
    """
    from core.currency import get_active_info

    try:
        info = get_active_info()
        simbolo = info['simbolo']
        sep_miles = info['sep_miles']
    except (KeyError, TypeError, AttributeError):
        simbolo = '$'
        sep_miles = '.'

    try:
        if monto is None or monto == '':
            monto = Decimal('0')
        if not isinstance(monto, Decimal):
            monto = Decimal(str(monto))
        monto = monto.quantize(Decimal('1'))
        negativo = monto < 0
        entero = abs(int(monto))
        texto = f'{entero:,}'.replace(',', sep_miles)
        prefijo = f'-{simbolo} ' if negativo else f'{simbolo} '
        return f'{prefijo}{texto}'
    except (InvalidOperation, ValueError, TypeError, AttributeError):
        return f'{simbolo} 0'

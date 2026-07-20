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
    """Formatea un monto como '$ 1.200.000' (sin decimales)."""
    if monto is None:
        monto = Decimal('0')
    if not isinstance(monto, Decimal):
        monto = Decimal(str(monto))
    monto = monto.quantize(Decimal('1'))
    negativo = monto < 0
    entero = abs(int(monto))
    texto = f'{entero:,}'.replace(',', '.')
    prefijo = '-$ ' if negativo else '$ '
    return f'{prefijo}{texto}'

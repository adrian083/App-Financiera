"""Multi-currency (display-only) support.

Stored amounts are never converted; the user simply chooses which currency
symbol / tag is shown across the UI. The active currency is resolved per
request from the logged-in user's configuration and kept in a thread-local so
the existing ``|cop`` template filter (and ``formato_cop``) stay currency-aware
without threading it through every call site.
"""
import threading

# code -> metadata
MONEDAS = {
    'COP': {'codigo': 'COP', 'simbolo': '$', 'nombre': 'Pesos', 'etiqueta': 'COP - Pesos', 'decimales': 0, 'sep_miles': '.'},
    'USD': {'codigo': 'USD', 'simbolo': '$', 'nombre': 'Dólares', 'etiqueta': 'USD - Dólares', 'decimales': 2, 'sep_miles': ','},
    'EUR': {'codigo': 'EUR', 'simbolo': '€', 'nombre': 'Euros', 'etiqueta': 'EUR - Euros', 'decimales': 2, 'sep_miles': '.'},
    'MXN': {'codigo': 'MXN', 'simbolo': '$', 'nombre': 'Pesos MXN', 'etiqueta': 'MXN - Pesos', 'decimales': 2, 'sep_miles': ','},
    'GBP': {'codigo': 'GBP', 'simbolo': '£', 'nombre': 'Libras', 'etiqueta': 'GBP - Libras', 'decimales': 2, 'sep_miles': ','},
    'BRL': {'codigo': 'BRL', 'simbolo': 'R$', 'nombre': 'Reales', 'etiqueta': 'BRL - Reales', 'decimales': 2, 'sep_miles': '.'},
    'GTQ': {'codigo': 'GTQ', 'simbolo': 'Q', 'nombre': 'Quetzales', 'etiqueta': 'GTQ - Quetzales', 'decimales': 2, 'sep_miles': ','},
}

DEFAULT_MONEDA = 'COP'

_state = threading.local()


def moneda_choices():
    return [(code, m['etiqueta']) for code, m in MONEDAS.items()]


def get_moneda_info(codigo):
    return MONEDAS.get(codigo, MONEDAS[DEFAULT_MONEDA])


def set_active_currency(codigo):
    _state.moneda = codigo if codigo in MONEDAS else DEFAULT_MONEDA


def get_active_currency():
    return getattr(_state, 'moneda', DEFAULT_MONEDA)


def get_active_info():
    return get_moneda_info(get_active_currency())

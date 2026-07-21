"""Template context processors for FinanzasApp."""
from core.currency import MONEDAS, get_active_info


def moneda(request):
    """Expose the active currency + full list for selectors and badges."""
    return {
        'moneda_activa': get_active_info(),
        'monedas_disponibles': list(MONEDAS.values()),
    }

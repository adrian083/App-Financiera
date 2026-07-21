"""Template context processors for FinanzasApp."""
from core.currency import MONEDAS, get_active_info


def moneda(request):
    """Expose the active currency + full list for selectors and badges."""
    context = {
        'moneda_activa': get_active_info(),
        'monedas_disponibles': list(MONEDAS.values()),
    }
    
    # Agregar configuración del usuario si está autenticado
    if request.user.is_authenticated:
        try:
            from presupuesto.models import ConfiguracionUsuario
            context['config'] = ConfiguracionUsuario.obtener(request.user)
        except Exception:
            context['config'] = None
    
    return context

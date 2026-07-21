"""Request middleware that resolves the active display currency per user."""
from core.currency import DEFAULT_MONEDA, set_active_currency


class CurrencyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        codigo = DEFAULT_MONEDA
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            try:
                from presupuesto.models import ConfiguracionUsuario
                config = ConfiguracionUsuario.obtener(user)
                codigo = config.moneda or DEFAULT_MONEDA
            except Exception:
                codigo = DEFAULT_MONEDA
        set_active_currency(codigo)
        try:
            response = self.get_response(request)
        finally:
            set_active_currency(DEFAULT_MONEDA)
        return response

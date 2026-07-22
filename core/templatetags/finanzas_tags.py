from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from core.utils.moneda import formato_cop

register = template.Library()


@register.filter
def cop(valor):
    """Formatea un monto y lo envuelve para el Modo Privacidad.

    El texto real queda dentro de un <span class="monto-dinero"> que el modo
    privacidad puede ocultar visualmente reemplazándolo por asteriscos.
    """
    return format_html('<span class="monto-dinero">{}</span>', formato_cop(valor))


@register.filter
def cop_plain(valor):
    """Formatea un monto sin el envoltorio de privacidad.

    Úsalo cuando el resultado se coloca dentro de un atributo HTML
    (por ejemplo el value de un input), donde no puede ir un <span>.
    """
    return formato_cop(valor)


@register.filter
def dict_get(d, key):
    return d.get(key) if d else None


@register.filter
def multiply(value, arg):
    """Multiply value by arg."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value


@register.filter
def subtract(value, arg):
    """Subtract arg from value."""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return value


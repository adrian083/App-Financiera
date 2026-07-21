from django import template

from core.utils.moneda import formato_cop

register = template.Library()


@register.filter
def cop(valor):
    return formato_cop(valor)


@register.filter
def dict_get(d, key):
    return d.get(key) if d else None


from django.contrib import admin

from ahorros.models import FondoAhorro, Inversion, MovimientoPatrimonio


@admin.register(FondoAhorro)
class FondoAhorroAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'saldo_disponible', 'actualizado')


@admin.register(MovimientoPatrimonio)
class MovimientoPatrimonioAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'descripcion', 'monto', 'usuario', 'fecha')
    list_filter = ('tipo', 'usuario')


@admin.register(Inversion)
class InversionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'usuario', 'monto_inicial', 'estado', 'fecha_vencimiento')
    list_filter = ('usuario', 'estado')

from django.contrib import admin

from presupuesto.models import (
    Categoria,
    CicloMensual,
    ConfiguracionUsuario,
    GastoFijoPlantilla,
    Movimiento,
)


@admin.register(ConfiguracionUsuario)
class ConfiguracionUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'salario_base', 'dia_corte', 'dias_plazo_tolerancia', 'configurado', 'ha_visto_tutorial')
    search_fields = ('usuario__username',)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'usuario', 'color', 'activa')
    list_filter = ('usuario',)


@admin.register(CicloMensual)
class CicloMensualAdmin(admin.ModelAdmin):
    list_display = ('etiqueta', 'usuario', 'salario_ciclo', 'estado')
    list_filter = ('estado', 'usuario')


@admin.register(GastoFijoPlantilla)
class GastoFijoPlantillaAdmin(admin.ModelAdmin):
    list_display = ('descripcion', 'usuario', 'monto', 'categoria', 'activa')


@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'descripcion', 'monto', 'usuario', 'ciclo')
    list_filter = ('tipo', 'usuario')

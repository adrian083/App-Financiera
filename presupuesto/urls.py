from django.urls import path

from presupuesto import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('configuracion/', views.configuracion_inicial, name='configuracion_inicial'),
    path('configuracion/editar/', views.configuracion_editar, name='configuracion_editar'),
    path('confirmar-ciclo/', views.confirmar_ciclo, name='confirmar_ciclo'),
    path('ocultar-banner-pago/', views.ocultar_banner_pago, name='ocultar_banner_pago'),
    path('gasto/', views.registrar_gasto, name='registrar_gasto'),
    path('ingreso/', views.registrar_ingreso, name='registrar_ingreso'),
    path('envio-ahorro/', views.registrar_envio_ahorro, name='registrar_envio_ahorro'),
    path('cerrar-ciclo/', views.cerrar_ciclo_view, name='cerrar_ciclo'),
    path('historico/', views.historico_meses, name='historico_meses'),
    path('ciclo/<int:pk>/', views.detalle_ciclo, name='detalle_ciclo'),
    path('categorias/', views.categorias_lista, name='categorias_lista'),
    path('categorias/crear/', views.categoria_crear, name='categoria_crear'),
    path('gastos-fijos/', views.gastos_fijos_lista, name='gastos_fijos_lista'),
    path('gastos-fijos/crear/', views.gasto_fijo_crear, name='gasto_fijo_crear'),
    path('tutorial/completar/', views.completar_tutorial, name='completar_tutorial'),
]

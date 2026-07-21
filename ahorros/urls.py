from django.urls import path

from ahorros import views

urlpatterns = [
    path('', views.dashboard_ahorros, name='dashboard_ahorros'),
    path('retirar/', views.retirar_view, name='retirar_ahorro'),
    path('inversion/crear/', views.crear_inversion_view, name='crear_inversion'),
    path('inversion/<int:pk>/cerrar/', views.cerrar_inversion_view, name='cerrar_inversion'),
    path('metas/', views.metas_ahorro, name='metas_ahorro'),
    path('metas/crear/', views.crear_meta, name='crear_meta'),
    path('metas/<int:meta_id>/deposito/', views.agregar_deposito_meta, name='agregar_deposito_meta'),
    path('metas/<int:meta_id>/eliminar/', views.eliminar_meta, name='eliminar_meta'),
    path('inversiones/', views.inversiones_detalle, name='inversiones_detalle'),
]

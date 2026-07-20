from django.urls import path

from ahorros import views

urlpatterns = [
    path('', views.dashboard_ahorros, name='dashboard_ahorros'),
    path('retirar/', views.retirar_view, name='retirar_ahorro'),
    path('inversion/crear/', views.crear_inversion_view, name='crear_inversion'),
    path('inversion/<int:pk>/cerrar/', views.cerrar_inversion_view, name='cerrar_inversion'),
]

from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path, reverse_lazy
from django.views.generic import RedirectView

from core.views import FinanzasLoginView, FinanzasLogoutView, registro

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', FinanzasLoginView.as_view(), name='login'),
    path('logout/', FinanzasLogoutView.as_view(), name='logout'),
    path('registro/', registro, name='registro'),
    path('', include('presupuesto.urls')),
    path('ahorros/', include('ahorros.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

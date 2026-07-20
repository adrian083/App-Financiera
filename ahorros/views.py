from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ahorros.forms import CierreInversionForm, InversionForm, RetiroAhorroForm
from ahorros.models import FondoAhorro, Inversion, MovimientoPatrimonio
from ahorros.services import (
    cerrar_inversion,
    crear_inversion,
    inversiones_pendientes_cierre,
    inversiones_proximas_vencer,
    retirar_ahorro,
)
from presupuesto.models import CicloMensual
from presupuesto.services import asegurar_ciclo_activo


@login_required
def dashboard_ahorros(request):
    user = request.user
    fondo = FondoAhorro.obtener(user)
    inversiones = Inversion.objects.filter(usuario=user)
    movimientos = MovimientoPatrimonio.objects.filter(usuario=user)[:20]

    context = {
        'fondo': fondo,
        'monto_congelado': Inversion.monto_congelado(user),
        'total_ganancias': Inversion.total_ganancias(user),
        'total_perdidas': Inversion.total_perdidas(user),
        'inversiones': inversiones,
        'inversiones_activas': inversiones.filter(
            estado__in=[Inversion.ACTIVA, Inversion.EN_CURSO, Inversion.VENCIDA_PENDIENTE],
        ),
        'movimientos': movimientos,
        'inversiones_vencidas': inversiones_pendientes_cierre(user),
        'inversiones_proximas': inversiones_proximas_vencer(user),
        'form_retiro': RetiroAhorroForm(),
        'form_inversion': InversionForm(),
    }
    return render(request, 'ahorros/dashboard.html', context)


@login_required
@require_POST
def retirar_view(request):
    ciclo = asegurar_ciclo_activo(request.user)
    if not ciclo or ciclo.estado != CicloMensual.ACTIVO:
        messages.error(request, 'No hay un ciclo activo.')
        return redirect('dashboard_ahorros')

    form = RetiroAhorroForm(request.POST)
    if form.is_valid():
        try:
            retirar_ahorro(
                request.user,
                form.cleaned_data['monto'],
                form.cleaned_data.get('descripcion', ''),
                ciclo,
            )
            messages.success(request, 'Retiro registrado e inyectado al ciclo actual.')
        except ValueError as e:
            messages.error(request, str(e))
    else:
        messages.error(request, 'Error en el formulario de retiro.')
    return redirect('dashboard_ahorros')


@login_required
@require_POST
def crear_inversion_view(request):
    form = InversionForm(request.POST)
    if form.is_valid():
        try:
            crear_inversion(
                request.user,
                form.cleaned_data['nombre'],
                form.cleaned_data['monto'],
                form.cleaned_data['fecha_vencimiento'],
                form.cleaned_data.get('notas', ''),
            )
            messages.success(request, 'Inversión creada.')
        except ValueError as e:
            messages.error(request, str(e))
    else:
        messages.error(request, 'Error al crear la inversión.')
    return redirect('dashboard_ahorros')


@login_required
@require_POST
def cerrar_inversion_view(request, pk):
    inversion = get_object_or_404(Inversion, pk=pk, usuario=request.user)
    form = CierreInversionForm(request.POST)
    if form.is_valid():
        if form.cleaned_data.get('extender'):
            cerrar_inversion(
                request.user, inversion, inversion.monto_inicial,
                extender=True, nueva_fecha=form.cleaned_data['nueva_fecha'],
            )
            messages.info(request, f'Plazo de "{inversion.nombre}" extendido.')
        else:
            inv = cerrar_inversion(request.user, inversion, form.cleaned_data['monto_final'])
            if inv.estado == Inversion.CERRADA_GANANCIA:
                messages.success(request, 'Inversión cerrada con ganancia.')
            elif inv.estado == Inversion.CERRADA_PERDIDA:
                messages.warning(request, 'Inversión cerrada con pérdida de capital.')
            else:
                messages.success(request, 'Inversión cerrada.')
    else:
        messages.error(request, 'Error al cerrar la inversión.')
    return redirect(request.POST.get('next', 'dashboard'))

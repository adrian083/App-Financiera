from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ahorros.forms import CierreInversionForm, InversionForm, RetiroAhorroForm
from ahorros.models import DepositoMeta, FondoAhorro, Inversion, MetaAhorro, MovimientoPatrimonio
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


@login_required
def metas_ahorro(request):
    user = request.user
    metas = MetaAhorro.objects.filter(usuario=user)
    fondo = FondoAhorro.obtener(user)
    total_ahorrado = MetaAhorro.total_ahorrado(user)
    total_objetivo = MetaAhorro.total_objetivo(user)
    porcentaje = round((total_ahorrado / total_objetivo * 100) if total_objetivo > 0 else 0, 1)
    
    context = {
        'metas': metas,
        'total_ahorrado': total_ahorrado,
        'total_objetivo': total_objetivo,
        'porcentaje': porcentaje,
        'fondo': fondo,
    }
    return render(request, 'ahorros/metas.html', context)


@login_required
@require_POST
def crear_meta(request):
    from ahorros.forms import MetaAhorroForm
    form = MetaAhorroForm(request.POST)
    if form.is_valid():
        meta = form.save(commit=False)
        meta.usuario = request.user
        meta.save()
        messages.success(request, 'Meta de ahorro creada.')
    else:
        messages.error(request, 'Error al crear la meta.')
    return redirect('metas_ahorro')


@login_required
@require_POST
def agregar_deposito_meta(request, meta_id):
    meta = get_object_or_404(MetaAhorro, pk=meta_id, usuario=request.user)
    monto = request.POST.get('monto')
    nota = request.POST.get('nota', '')
    
    if not monto:
        messages.error(request, 'El monto es requerido.')
        return redirect('metas_ahorro')
    
    from core.utils.moneda import parse_cop
    monto_parsed = parse_cop(monto)
    
    if monto_parsed <= 0:
        messages.error(request, 'El monto debe ser mayor a cero.')
        return redirect('metas_ahorro')
    
    DepositoMeta.objects.create(
        meta=meta,
        monto=monto_parsed,
        nota=nota,
    )
    
    meta.saldo_actual += monto_parsed
    if meta.saldo_actual >= meta.monto_objetivo:
        meta.completada = True
    meta.save()
    
    messages.success(request, f'Aporte de {monto} agregado a {meta.nombre}.')
    return redirect('metas_ahorro')


@login_required
@require_POST
def eliminar_meta(request, meta_id):
    meta = get_object_or_404(MetaAhorro, pk=meta_id, usuario=request.user)
    meta.delete()
    messages.success(request, 'Meta eliminada.')
    return redirect('metas_ahorro')


@login_required
def inversiones_detalle(request):
    user = request.user
    inversiones = Inversion.objects.filter(usuario=user)
    distribucion = Inversion.distribucion_portafolio(user)
    monto_congelado = Inversion.monto_congelado(user)
    total_ganancias = Inversion.total_ganancias(user)
    total_perdidas = Inversion.total_perdidas(user)
    
    # Calcular ROI
    roi = round(((total_ganancias - total_perdidas) / monto_congelado * 100) if monto_congelado > 0 else 0, 1)
    
    # Calcular porcentajes de distribución
    for item in distribucion:
        item.porcentaje = round((item.total / monto_congelado * 100) if monto_congelado > 0 else 0, 1)
    
    context = {
        'inversiones': inversiones,
        'distribucion': distribucion,
        'monto_congelado': monto_congelado,
        'total_ganancias': total_ganancias,
        'total_perdidas': total_perdidas,
        'roi': roi,
    }
    return render(request, 'ahorros/inversiones.html', context)

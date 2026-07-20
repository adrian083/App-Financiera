import json

from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ahorros.models import FondoAhorro
from ahorros.services import (
    inversiones_pendientes_cierre,
    inversiones_proximas_vencer,
    registrar_envio_desde_presupuesto,
)
from presupuesto.forms import (
    CategoriaForm,
    CierreCicloForm,
    ConfiguracionForm,
    EnvioAhorroForm,
    GastoFijoPlantillaForm,
    IngresoForm,
    MovimientoForm,
)
from presupuesto.models import (
    Categoria,
    CicloMensual,
    ConfiguracionUsuario,
    GastoFijoPlantilla,
    Movimiento,
)
from presupuesto.services import (
    asegurar_ciclo_activo,
    cerrar_ciclo,
    confirmar_ciclo_pendiente,
    get_fechas_plazo_confirmacion,
    obtener_ciclo_en_plazo_confirmacion,
    verificar_cierre_pendiente,
)


def _config_ciclo(request):
    config = ConfiguracionUsuario.obtener(request.user)
    ciclo = CicloMensual.obtener_activo(request.user)
    if not ciclo:
        ciclo = CicloMensual.obtener_pendiente(request.user)
    return config, ciclo


@login_required
def dashboard(request):
    user = request.user
    config, ciclo = _config_ciclo(request)

    if not config.configurado:
        return redirect('configuracion_inicial')

    ciclo_pendiente_cierre = verificar_cierre_pendiente(user)
    if ciclo_pendiente_cierre:
        cerrar_ciclo(user, ciclo_pendiente_cierre, config.salario_base)
        messages.info(request, 'Tu ciclo se cerró automáticamente porque pasó el plazo de confirmación.')
        return redirect('confirmar_ciclo')

    ciclo_en_plazo_confirmacion = obtener_ciclo_en_plazo_confirmacion(user)
    if not ciclo and not ciclo_en_plazo_confirmacion:
        ciclo = asegurar_ciclo_activo(user)

    if ciclo and ciclo.estado == CicloMensual.PENDIENTE:
        return redirect('confirmar_ciclo')

    filtro = request.GET.get('filtro', 'todos')
    movimientos_qs = ciclo.movimientos.all() if ciclo else Movimiento.objects.none()
    if filtro == 'gasto':
        movimientos_qs = movimientos_qs.filter(tipo=Movimiento.GASTO)
    elif filtro == 'ingreso':
        movimientos_qs = movimientos_qs.filter(tipo=Movimiento.INGRESO_ADICIONAL)
    elif filtro == 'ahorro':
        movimientos_qs = movimientos_qs.filter(tipo__in=[Movimiento.ENVIO_AHORRO, Movimiento.INYECCION_AHORRO])

    chart_labels, chart_data, chart_colors = [], [], []
    if ciclo:
        for item in ciclo.gastos_por_categoria():
            chart_labels.append(item['categoria__nombre'])
            chart_data.append(int(item['total']))
            chart_colors.append(item['categoria__color'])

    fondo = FondoAhorro.obtener(user)
    inv_vencidas = inversiones_pendientes_cierre(user)
    inv_proximas = inversiones_proximas_vencer(user)

    ocultar_banner_pago = False
    banner_oculto_hasta = request.session.get('ocultar_banner_pago_hasta')
    if banner_oculto_hasta:
        try:
            ocultar_fecha = date.fromisoformat(banner_oculto_hasta)
        except ValueError:
            ocultar_fecha = None
        if ocultar_fecha and ocultar_fecha >= date.today():
            ocultar_banner_pago = True
        else:
            request.session.pop('ocultar_banner_pago_hasta', None)

    fechas_plazo = None
    if ciclo_en_plazo_confirmacion:
        fechas_plazo = get_fechas_plazo_confirmacion(
            ciclo_en_plazo_confirmacion,
            config.dias_plazo_tolerancia,
        )

    context = {
        'config': config,
        'ciclo': ciclo,
        'ciclo_pendiente_cierre': ciclo_pendiente_cierre,
        'ciclo_en_plazo_confirmacion': ciclo_en_plazo_confirmacion,
        'fechas_plazo_confirmacion': fechas_plazo,
        'ocultar_banner_pago': ocultar_banner_pago,
        'fondo': fondo,
        'inversiones_vencidas': inv_vencidas,
        'inversiones_proximas': inv_proximas,
        'filtro_actual': filtro,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        'chart_colors': json.dumps(chart_colors),
        'movimientos_recientes': movimientos_qs[:20],
        'form_gasto': MovimientoForm(usuario=user),
        'form_ingreso': IngresoForm(),
        'form_ahorro': EnvioAhorroForm(),
        'form_cierre': CierreCicloForm(initial={'nuevo_salario': config.salario_base}),
        'mostrar_tutorial': not config.ha_visto_tutorial,
    }
    return render(request, 'presupuesto/dashboard.html', context)


@login_required
def configuracion_inicial(request):
    config = ConfiguracionUsuario.obtener(request.user)
    if request.method == 'POST':
        form = ConfiguracionForm(request.POST, instance=config)
        if form.is_valid():
            config = form.save(commit=False)
            config.usuario = request.user
            config.configurado = True
            config.save()
            from presupuesto.services import crear_nuevo_ciclo
            crear_nuevo_ciclo(request.user, config.salario_base, config.dia_corte)
            messages.success(request, '¡Configuración guardada! Tu primer ciclo ha iniciado.')
            return redirect('dashboard')
    else:
        form = ConfiguracionForm(instance=config)
    return render(request, 'presupuesto/configuracion.html', {'form': form})


@login_required
def configuracion_editar(request):
    config = ConfiguracionUsuario.obtener(request.user)
    if request.method == 'POST':
        form = ConfiguracionForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuración actualizada.')
            return redirect('dashboard')
    else:
        form = ConfiguracionForm(instance=config)
    return render(request, 'presupuesto/configuracion.html', {'form': form, 'editando': True})


@login_required
def confirmar_ciclo(request):
    ciclo = CicloMensual.obtener_pendiente(request.user)
    if not ciclo:
        return redirect('dashboard')
    gastos_fijos = ciclo.movimientos.filter(es_gasto_fijo=True)
    if request.method == 'POST':
        for mov in gastos_fijos:
            key = f'monto_{mov.pk}'
            if key in request.POST:
                from core.utils.moneda import parse_cop
                mov.monto = parse_cop(request.POST[key])
                mov.save(update_fields=['monto'])
        confirmar_ciclo_pendiente(ciclo)
        messages.success(request, f'Ciclo "{ciclo.etiqueta}" confirmado y activo.')
        return redirect('dashboard')
    return render(request, 'presupuesto/confirmar_ciclo.html', {
        'ciclo': ciclo,
        'gastos_fijos': gastos_fijos,
    })


@login_required
def ocultar_banner_pago(request):
    request.session['ocultar_banner_pago_hasta'] = (date.today() + timedelta(days=1)).isoformat()
    return redirect('dashboard')


@login_required
@require_POST
@transaction.atomic
def registrar_gasto(request):
    ciclo = get_object_or_404(
        CicloMensual, pk=request.POST.get('ciclo_id'),
        usuario=request.user, estado=CicloMensual.ACTIVO,
    )
    form = MovimientoForm(request.POST, usuario=request.user)
    if form.is_valid():
        monto = form.cleaned_data['monto']
        descripcion = form.cleaned_data['descripcion']
        mov = Movimiento.objects.create(
            usuario=request.user,
            ciclo=ciclo,
            tipo=Movimiento.GASTO,
            monto=monto,
            descripcion=descripcion,
            categoria=form.cleaned_data['categoria'],
        )
        if form.cleaned_data.get('es_gasto_fijo'):
            GastoFijoPlantilla.objects.create(
                usuario=request.user,
                descripcion=descripcion,
                monto=monto,
                categoria=form.cleaned_data['categoria'],
            )
            mov.es_gasto_fijo = True
            mov.save(update_fields=['es_gasto_fijo'])
        messages.success(request, 'Gasto registrado correctamente.')
    else:
        for field, errs in form.errors.items():
            for e in errs:
                messages.error(request, f'{field}: {e}')
    return redirect('dashboard')


@login_required
@require_POST
def registrar_envio_ahorro(request):
    ciclo = get_object_or_404(
        CicloMensual, pk=request.POST.get('ciclo_id'),
        usuario=request.user, estado=CicloMensual.ACTIVO,
    )
    form = EnvioAhorroForm(request.POST)
    if form.is_valid():
        mov = Movimiento.objects.create(
            usuario=request.user,
            ciclo=ciclo,
            tipo=Movimiento.ENVIO_AHORRO,
            monto=form.cleaned_data['monto'],
            descripcion=form.cleaned_data['descripcion'],
        )
        registrar_envio_desde_presupuesto(request.user, mov)
        messages.success(request, 'Transferencia a ahorro registrada.')
    else:
        messages.error(request, 'Error al transferir a ahorro.')
    return redirect('dashboard')


@login_required
@require_POST
def registrar_ingreso(request):
    ciclo = get_object_or_404(
        CicloMensual, pk=request.POST.get('ciclo_id'),
        usuario=request.user, estado=CicloMensual.ACTIVO,
    )
    form = IngresoForm(request.POST)
    if form.is_valid():
        Movimiento.objects.create(
            usuario=request.user,
            ciclo=ciclo,
            tipo=Movimiento.INGRESO_ADICIONAL,
            monto=form.cleaned_data['monto'],
            descripcion=form.cleaned_data['descripcion'],
        )
        messages.success(request, 'Ingreso adicional registrado.')
    else:
        messages.error(request, 'Error al registrar ingreso.')
    return redirect('dashboard')


@login_required
@require_POST
@transaction.atomic
def cerrar_ciclo_view(request):
    ciclo = get_object_or_404(
        CicloMensual, pk=request.POST.get('ciclo_id'),
        usuario=request.user, estado=CicloMensual.ACTIVO,
    )
    form = CierreCicloForm(request.POST)
    if form.is_valid():
        nuevo = cerrar_ciclo(request.user, ciclo, form.cleaned_data['nuevo_salario'])
        messages.success(request, f'Ciclo cerrado. Revisa los gastos fijos del ciclo "{nuevo.etiqueta}".')
        return redirect('confirmar_ciclo')
    messages.error(request, 'Error al cerrar el ciclo.')
    return redirect('dashboard')


@login_required
def historico_meses(request):
    ciclos = CicloMensual.objects.filter(usuario=request.user, estado=CicloMensual.CERRADO)
    return render(request, 'presupuesto/historico.html', {'ciclos': ciclos})


@login_required
def detalle_ciclo(request, pk):
    ciclo = get_object_or_404(CicloMensual, pk=pk, usuario=request.user)
    gastos_cat = ciclo.gastos_por_categoria()
    return render(request, 'presupuesto/detalle_ciclo.html', {
        'ciclo': ciclo,
        'movimientos': ciclo.movimientos.all(),
        'chart_labels': json.dumps([g['categoria__nombre'] for g in gastos_cat]),
        'chart_data': json.dumps([int(g['total']) for g in gastos_cat]),
        'chart_colors': json.dumps([g['categoria__color'] for g in gastos_cat]),
    })


@login_required
def categorias_lista(request):
    categorias = Categoria.objects.filter(usuario=request.user)
    return render(request, 'presupuesto/categorias.html', {
        'categorias': categorias,
        'form': CategoriaForm(),
    })


@login_required
@require_POST
def categoria_crear(request):
    form = CategoriaForm(request.POST)
    if form.is_valid():
        cat = form.save(commit=False)
        cat.usuario = request.user
        cat.save()
        messages.success(request, 'Categoría creada.')
    else:
        messages.error(request, 'Error al crear categoría.')
    return redirect('categorias_lista')


@login_required
def gastos_fijos_lista(request):
    plantillas = GastoFijoPlantilla.objects.filter(usuario=request.user)
    return render(request, 'presupuesto/gastos_fijos.html', {
        'plantillas': plantillas,
        'form': GastoFijoPlantillaForm(usuario=request.user),
    })


@login_required
@require_POST
def gasto_fijo_crear(request):
    form = GastoFijoPlantillaForm(request.POST, usuario=request.user)
    if form.is_valid():
        plantilla = form.save(commit=False)
        plantilla.usuario = request.user
        plantilla.save()
        messages.success(request, 'Gasto fijo agregado a plantillas.')
    else:
        messages.error(request, 'Error al crear gasto fijo.')
    return redirect('gastos_fijos_lista')


@login_required
@require_POST
def completar_tutorial(request):
    config = ConfiguracionUsuario.obtener(request.user)
    config.ha_visto_tutorial = True
    config.save(update_fields=['ha_visto_tutorial'])
    return JsonResponse({'ok': True})

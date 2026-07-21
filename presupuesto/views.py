import json
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

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
    EventoCalendario,
    GastoFijoPlantilla,
    Movimiento,
    WidgetConfiguracion,
)
from ahorros.models import FondoAhorro, Inversion, MetaAhorro, MovimientoPatrimonio
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
    gastos_categoria = ciclo.gastos_por_categoria() if ciclo else []
    for item in gastos_categoria:
        chart_labels.append(item['categoria__nombre'])
        chart_data.append(int(item['total']))
        chart_colors.append(item['categoria__color'])

    # Serie histórica del balance (sobrante por ciclo cerrado + ciclo actual)
    ciclos_cerrados = list(
        CicloMensual.objects.filter(usuario=user, estado=CicloMensual.CERRADO)
        .order_by('fecha_inicio')
    )
    balance_labels, balance_data = [], []
    for c in ciclos_cerrados:
        balance_labels.append(c.fecha_inicio.strftime('%d/%m'))
        balance_data.append(int(c.sobrante_transferido))
    if ciclo:
        balance_labels.append('Actual')
        balance_data.append(int(ciclo.saldo_disponible()))

    fondo = FondoAhorro.obtener(user)
    inv_vencidas = inversiones_pendientes_cierre(user)
    inv_proximas = inversiones_proximas_vencer(user)
    
    # Datos para widgets adicionales
    from ahorros.models import Inversion, MetaAhorro
    from presupuesto.models import GastoFijoPlantilla, EventoCalendario
    from datetime import date, timedelta
    
    inversiones_activas = Inversion.objects.filter(usuario=user, estado=Inversion.ACTIVA)
    metas_ahorro = MetaAhorro.objects.filter(usuario=user)
    gastos_fijos = GastoFijoPlantilla.objects.filter(usuario=user, activa=True)
    proximos_eventos = EventoCalendario.objects.filter(
        usuario=user,
        fecha__gte=date.today(),
        fecha__lte=date.today() + timedelta(days=30)
    ).order_by('fecha')[:5]

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
        'gastos_categoria': gastos_categoria,
        'balance_labels': json.dumps(balance_labels),
        'balance_data': json.dumps(balance_data),
        'movimientos_recientes': movimientos_qs[:20],
        'widget_config': WidgetConfiguracion.obtener(user),
        'form_gasto': MovimientoForm(usuario=user),
        'form_ingreso': IngresoForm(),
        'form_ahorro': EnvioAhorroForm(),
        'form_cierre': CierreCicloForm(initial={'nuevo_salario': config.salario_base}),
        'mostrar_tutorial': not config.ha_visto_tutorial,
        # Datos para widgets
        'inversiones_activas': inversiones_activas,
        'metas_ahorro': metas_ahorro,
        'gastos_fijos': gastos_fijos,
        'proximos_eventos': proximos_eventos,
    }
    return render(request, 'presupuesto/dashboard.html', context)


@login_required
def configuracion_inicial(request):
    try:
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
                messages.error(request, 'Error al guardar configuración. Por favor verifica los datos.')
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
        else:
            form = ConfiguracionForm(instance=config)
        return render(request, 'presupuesto/configuracion.html', {'form': form})
    except Exception as e:
        messages.error(request, f'Error inesperado al cargar configuración: {str(e)}')
        return redirect('dashboard')


@login_required
def configuracion_editar(request):
    try:
        config = ConfiguracionUsuario.obtener(request.user)
        if request.method == 'POST':
            form = ConfiguracionForm(request.POST, instance=config)
            if form.is_valid():
                form.save()
                messages.success(request, 'Configuración actualizada correctamente.')
                return redirect('dashboard')
            else:
                messages.error(request, 'Error al guardar configuración. Por favor verifica los datos.')
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
        else:
            form = ConfiguracionForm(instance=config)
        return render(request, 'presupuesto/configuracion.html', {'form': form, 'editando': True})
    except Exception as e:
        messages.error(request, f'Error inesperado al cargar configuración: {str(e)}')
        return redirect('dashboard')


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
def historico_pdf(request):
    """Generar PDF del histórico de ciclos cerrados."""
    if not REPORTLAB_AVAILABLE:
        messages.error(request, 'La librería reportlab no está instalada. Contacta al administrador.')
        return redirect('historico_meses')
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="historico_{request.user.username}_{datetime.now().strftime("%Y%m%d")}.pdf"'
    
    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Estilo personalizado para el título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#10B981'),
        spaceAfter=30,
    )
    
    # Título
    elements.append(Paragraph(f"Histórico Financiero - {request.user.username}", title_style))
    elements.append(Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Obtener ciclos cerrados
    ciclos = CicloMensual.objects.filter(usuario=request.user, estado=CicloMensual.CERRADO).order_by('-fecha_cierre')
    
    if not ciclos:
        elements.append(Paragraph("No hay ciclos cerrados para mostrar.", styles['Normal']))
    else:
        # Crear tabla de datos
        data = [['Ciclo', 'Fecha Inicio', 'Fecha Cierre', 'Salario', 'Ingresos', 'Gastos', 'Sobrante']]
        
        for ciclo in ciclos:
            data.append([
                ciclo.etiqueta,
                ciclo.fecha_inicio.strftime('%d/%m/%Y'),
                ciclo.fecha_cierre.strftime('%d/%m/%Y') if ciclo.fecha_cierre else '-',
                f"${ciclo.salario_ciclo:,.0f}",
                f"${ciclo.total_ingresos():,.0f}",
                f"${ciclo.total_gastos():,.0f}",
                f"${ciclo.sobrante_transferido:,.0f}",
            ])
        
        # Estilo de la tabla
        table = Table(data, colWidths=[1.5*inch, 1.2*inch, 1.2*inch, 1*inch, 1*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10B981')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F3F4F6')),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
        ]))
        
        elements.append(table)
    
    # Pie de página
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("FinanzasApp - Gestión de Finanzas Personales", styles['Normal']))
    
    doc.build(elements)
    return response



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
    config = ConfiguracionUsuario.obtener(request.user)
    return render(request, 'presupuesto/categorias.html', {
        'categorias': categorias,
        'total_categorias': categorias.count(),
        'total_activas': categorias.filter(activa=True).count(),
        'config': config,
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
    from django.db.models import Sum

    plantillas = GastoFijoPlantilla.objects.filter(usuario=request.user)
    activas = plantillas.filter(activa=True)
    total_fijo = activas.aggregate(t=Sum('monto'))['t'] or 0
    return render(request, 'presupuesto/gastos_fijos.html', {
        'plantillas': plantillas,
        'total_fijo': total_fijo,
        'total_plantillas': plantillas.count(),
        'total_activas': activas.count(),
        'total_inactivas': plantillas.filter(activa=False).count(),
        'form': GastoFijoPlantillaForm(usuario=request.user),
    })


@login_required
@require_POST
def gasto_fijo_crear(request):
    try:
        form = GastoFijoPlantillaForm(request.POST, usuario=request.user)
        if form.is_valid():
            plantilla = form.save(commit=False)
            plantilla.usuario = request.user
            plantilla.save()
            
            # Agregar gasto al ciclo actual si existe
            ciclo = CicloMensual.obtener_activo(request.user)
            if ciclo:
                try:
                    Movimiento.objects.create(
                        usuario=request.user,
                        ciclo=ciclo,
                        categoria=plantilla.categoria,
                        monto=plantilla.monto,
                        descripcion=plantilla.descripcion,
                        tipo=Movimiento.GASTO,
                        es_gasto_fijo=True,
                        plantilla_origen=plantilla,
                    )
                    messages.success(request, 'Gasto fijo agregado a plantillas y al ciclo actual.')
                except Exception as e:
                    messages.error(request, f'Gasto fijo agregado a plantillas pero error al agregar al ciclo: {str(e)}')
            else:
                messages.success(request, 'Gasto fijo agregado a plantillas. No hay ciclo activo.')
        else:
            messages.error(request, 'Error al crear gasto fijo. Por favor verifica los datos.')
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    except Exception as e:
        messages.error(request, f'Error inesperado al crear gasto fijo: {str(e)}')
    return redirect('gastos_fijos_lista')


@login_required
@require_POST
def completar_tutorial(request):
    config = ConfiguracionUsuario.obtener(request.user)
    config.ha_visto_tutorial = True
    config.save(update_fields=['ha_visto_tutorial'])
    return JsonResponse({'ok': True})


@login_required
def gasto_fijo_editar(request, pk):
    plantilla = get_object_or_404(GastoFijoPlantilla, pk=pk, usuario=request.user)
    if request.method == 'POST':
        form = GastoFijoPlantillaForm(request.POST, instance=plantilla, usuario=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Gasto fijo actualizado.')
            return redirect('gastos_fijos_lista')
    else:
        form = GastoFijoPlantillaForm(instance=plantilla, usuario=request.user)
    return render(request, 'presupuesto/gastos_fijos.html', {
        'form': form,
        'editando_id': pk,
        'plantillas': GastoFijoPlantilla.objects.filter(usuario=request.user),
        'total_fijo': GastoFijoPlantilla.objects.filter(usuario=request.user, activa=True).aggregate(t=Sum('monto'))['t'] or 0,
        'total_plantillas': GastoFijoPlantilla.objects.filter(usuario=request.user).count(),
        'total_activas': GastoFijoPlantilla.objects.filter(usuario=request.user, activa=True).count(),
        'total_inactivas': GastoFijoPlantilla.objects.filter(usuario=request.user, activa=False).count(),
    })


@login_required
@require_POST
def gasto_fijo_eliminar(request, pk):
    plantilla = get_object_or_404(GastoFijoPlantilla, pk=pk, usuario=request.user)
    plantilla.delete()
    messages.success(request, 'Gasto fijo eliminado.')
    return redirect('gastos_fijos_lista')


@login_required
@require_POST
def gasto_fijo_toggle_activa(request, pk):
    plantilla = get_object_or_404(GastoFijoPlantilla, pk=pk, usuario=request.user)
    plantilla.activa = not plantilla.activa
    plantilla.save()
    estado = 'activada' if plantilla.activa else 'desactivada'
    messages.success(request, f'Gasto fijo {estado}.')
    return redirect('gastos_fijos_lista')


@login_required
def editar_gasto(request, gasto_id):
    movimiento = get_object_or_404(Movimiento, pk=gasto_id, usuario=request.user)
    if request.method == 'POST':
        form = MovimientoForm(request.POST, usuario=request.user)
        if form.is_valid():
            movimiento.descripcion = form.cleaned_data['descripcion']
            movimiento.monto = form.cleaned_data['monto']
            movimiento.categoria = form.cleaned_data.get('categoria')
            movimiento.save(update_fields=['descripcion', 'monto', 'categoria'])
            messages.success(request, 'Gasto actualizado.')
            return redirect('dashboard')
    else:
        form = MovimientoForm(
            initial={
                'descripcion': movimiento.descripcion,
                'monto': movimiento.monto,
                'categoria': movimiento.categoria,
            },
            usuario=request.user,
        )
    return render(request, 'presupuesto/dashboard.html', {
        'form_gasto': form,
        'editando_gasto_id': gasto_id,
        'config': ConfiguracionUsuario.obtener(request.user),
        'ciclo': CicloMensual.obtener_activo(request.user),
    })


@login_required
@require_POST
def eliminar_gasto(request, gasto_id):
    movimiento = get_object_or_404(Movimiento, pk=gasto_id, usuario=request.user)
    if movimiento.tipo != Movimiento.GASTO:
        messages.error(request, 'Solo se pueden eliminar gastos.')
        return redirect('dashboard')
    movimiento.delete()
    messages.success(request, 'Gasto eliminado.')
    return redirect('dashboard')


@login_required
def calendario_view(request):
    import calendar
    from datetime import datetime, date
    
    # Obtener mes y año de query params o usar actual
    year = int(request.GET.get('year', date.today().year))
    month = int(request.GET.get('month', date.today().month))
    
    # Obtener eventos del mes
    primer_dia = date(year, month, 1)
    ultimo_dia = date(year, month, calendar.monthrange(year, month)[1])
    
    eventos = EventoCalendario.objects.filter(
        usuario=request.user,
        fecha__gte=primer_dia,
        fecha__lte=ultimo_dia,
    ).order_by('fecha')
    
    # Crear diccionario de eventos por día
    eventos_por_dia = {}
    for evento in eventos:
        dia = evento.fecha.day
        if dia not in eventos_por_dia:
            eventos_por_dia[dia] = []
        eventos_por_dia[dia].append(evento)
    
    # Crear lista de días con eventos para fácil acceso en template
    dias_con_eventos = list(eventos_por_dia.keys())
    
    # Generar calendario
    cal = calendar.Calendar()
    semanas = cal.monthdayscalendar(year, month)
    
    # Nombres de días en español
    dias_semana = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']
    meses_es = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    
    # Navegación mes anterior/siguiente
    mes_anterior = month - 1 if month > 1 else 12
    año_anterior = year if month > 1 else year - 1
    mes_siguiente = month + 1 if month < 12 else 1
    año_siguiente = year if month < 12 else year + 1
    
    context = {
        'year': year,
        'month': month,
        'mes_nombre': meses_es[month - 1],
        'semanas': semanas,
        'dias_semana': dias_semana,
        'eventos_por_dia': eventos_por_dia,
        'mes_anterior': mes_anterior,
        'año_anterior': año_anterior,
        'mes_siguiente': mes_siguiente,
        'año_siguiente': año_siguiente,
        'hoy': date.today(),
    }
    return render(request, 'presupuesto/calendario.html', context)


@login_required
@require_POST
def crear_evento_calendario(request):
    from core.utils.moneda import parse_cop
    
    titulo = request.POST.get('titulo')
    fecha = request.POST.get('fecha')
    tipo = request.POST.get('tipo', EventoCalendario.OTRO)
    monto_str = request.POST.get('monto')
    descripcion = request.POST.get('descripcion', '')
    repetir_anualmente = request.POST.get('repetir_anualmente') == 'on'
    
    if not titulo or not fecha:
        messages.error(request, 'El título y la fecha son requeridos.')
        return redirect('calendario')
    
    monto = None
    if monto_str:
        monto = parse_cop(monto_str)
    
    EventoCalendario.objects.create(
        usuario=request.user,
        titulo=titulo,
        descripcion=descripcion,
        fecha=fecha,
        tipo=tipo,
        monto=monto,
        repetir_anualmente=repetir_anualmente,
    )
    
    messages.success(request, 'Evento creado exitosamente.')
    return redirect('calendario')


@login_required
def personalizar_widgets(request):
    widget_config = WidgetConfiguracion.obtener(request.user)
    
    # Todos los widgets disponibles
    widgets_disponibles = [
        {'id': 'saldo_disponible', 'nombre': 'Saldo disponible', 'icono': 'fa-wallet', 'descripcion': 'Monto disponible en el ciclo actual'},
        {'id': 'gastos_categoria', 'nombre': 'Gastos por categoría', 'icono': 'fa-chart-pie', 'descripcion': 'Distribución de gastos por categoría'},
        {'id': 'presupuesto_gastado', 'nombre': 'Presupuesto gastado', 'icono': 'fa-chart-line', 'descripcion': 'Progreso del presupuesto mensual'},
        {'id': 'ahorros_resumen', 'nombre': 'Resumen de ahorros', 'icono': 'fa-piggy-bank', 'descripcion': 'Estado del fondo de ahorros'},
        {'id': 'inversiones_activas', 'nombre': 'Inversiones activas', 'icono': 'fa-chart-bar', 'descripcion': 'Inversiones en curso y ROI'},
        {'id': 'proximos_pagos', 'nombre': 'Próximos pagos', 'icono': 'fa-calendar-check', 'descripcion': 'Eventos del calendario próximos'},
        {'id': 'gastos_fijos_resumen', 'nombre': 'Gastos fijos', 'icono': 'fa-receipt', 'descripcion': 'Resumen de gastos fijos mensuales'},
        {'id': 'metas_ahorro', 'nombre': 'Metas de ahorro', 'icono': 'fa-bullseye', 'descripcion': 'Progreso hacia metas financieras'},
    ]
    
    if request.method == 'POST':
        widgets_seleccionados = request.POST.getlist('widgets')
        widget_config.widgets_activos = widgets_seleccionados
        widget_config.save()
        messages.success(request, 'Widgets actualizados.')
        return redirect('dashboard')
    
    # Usar widgets activos o por defecto
    widgets_activos = widget_config.widgets_activos if widget_config.widgets_activos else widget_config.widgets_por_defecto()
    
    context = {
        'widgets_disponibles': widgets_disponibles,
        'widgets_activos': widgets_activos,
    }
    return render(request, 'presupuesto/personalizar_widgets.html', context)


@login_required
def backup_descargar(request):
    """Descargar backup de todos los datos del usuario en formato JSON."""
    user = request.user
    
    # Recopilar todos los datos
    datos = {
        'backup_fecha': datetime.now().isoformat(),
        'usuario': {
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'date_joined': user.date_joined.isoformat(),
        },
        'configuracion': _serialize_configuracion(user),
        'categorias': _serialize_categorias(user),
        'movimientos': _serialize_movimientos(user),
        'ciclos': _serialize_ciclos(user),
        'gastos_fijos': _serialize_gastos_fijos(user),
        'eventos_calendario': _serialize_eventos(user),
        'fondo_ahorro': _serialize_fondo_ahorro(user),
        'inversiones': _serialize_inversiones(user),
        'metas_ahorro': _serialize_metas_ahorro(user),
        'movimientos_patrimonio': _serialize_movimientos_patrimonio(user),
        'widgets_config': _serialize_widgets_config(user),
    }
    
    # Crear respuesta HTTP con archivo JSON
    response = HttpResponse(
        json.dumps(datos, ensure_ascii=False, indent=2),
        content_type='application/json'
    )
    response['Content-Disposition'] = f'attachment; filename="backup_{user.username}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
    return response


@login_required
def backup_restaurar(request):
    """Restaurar datos desde un archivo JSON de backup."""
    if request.method == 'POST':
        archivo = request.FILES.get('archivo_backup')
        if not archivo:
            messages.error(request, 'Por favor selecciona un archivo de backup.')
            return redirect('backup_gestion')
        
        try:
            datos = json.loads(archivo.read().decode('utf-8'))
        except json.JSONDecodeError:
            messages.error(request, 'El archivo no es un JSON válido.')
            return redirect('backup_gestion')
        
        try:
            with transaction.atomic():
                # Restaurar configuración
                _restore_configuracion(request.user, datos.get('configuracion'))
                
                # Restaurar categorías
                _restore_categorias(request.user, datos.get('categorias', []))
                
                # Restaurar gastos fijos
                _restore_gastos_fijos(request.user, datos.get('gastos_fijos', []))
                
                # Restaurar eventos de calendario
                _restore_eventos(request.user, datos.get('eventos_calendario', []))
                
                # Restaurar metas de ahorro
                _restore_metas_ahorro(request.user, datos.get('metas_ahorro', []))
                
                # Restaurar configuración de widgets
                _restore_widgets_config(request.user, datos.get('widgets_config'))
                
                messages.success(request, 'Backup restaurado exitosamente.')
                messages.warning(request, 'Nota: Movimientos, ciclos e inversiones no fueron restaurados para evitar inconsistencias.')
        except Exception as e:
            messages.error(request, f'Error al restaurar backup: {str(e)}')
            return redirect('backup_gestion')
        
        return redirect('dashboard')
    
    return render(request, 'presupuesto/backup_gestion.html')


@login_required
def backup_gestion(request):
    """Página de gestión de backups."""
    return render(request, 'presupuesto/backup_gestion.html')


# Funciones auxiliares para serialización
def _serialize_configuracion(user):
    try:
        config = ConfiguracionUsuario.objects.get(usuario=user)
        return {
            'salario_base': str(config.salario_base),
            'dia_corte': config.dia_corte,
            'dias_plazo_tolerancia': config.dias_plazo_tolerancia,
            'moneda': config.moneda,
            'configurado': config.configurado,
            'ha_visto_tutorial': config.ha_visto_tutorial,
        }
    except ConfiguracionUsuario.DoesNotExist:
        return None


def _serialize_categorias(user):
    try:
        return list(Categoria.objects.filter(usuario=user).values(
            'nombre', 'color', 'presupuesto_mensual'
        ))
    except Exception:
        # Fallback si no tiene presupuesto_mensual
        return list(Categoria.objects.filter(usuario=user).values(
            'nombre', 'color'
        ))


def _serialize_movimientos(user):
    movimientos = []
    for mov in Movimiento.objects.filter(usuario=user):
        movimientos.append({
            'tipo': mov.tipo,
            'monto': str(mov.monto),
            'descripcion': mov.descripcion,
            'categoria_nombre': mov.categoria.nombre if mov.categoria else None,
            'es_gasto_fijo': mov.es_gasto_fijo,
            'pagado': mov.pagado,
            'fecha_registro': mov.fecha_registro.isoformat(),
            'fecha_vencimiento': mov.fecha_vencimiento.isoformat() if mov.fecha_vencimiento else None,
        })
    return movimientos


def _serialize_ciclos(user):
    ciclos = []
    for ciclo in CicloMensual.objects.filter(usuario=user):
        ciclos.append({
            'fecha_inicio': ciclo.fecha_inicio.isoformat(),
            'fecha_cierre': ciclo.fecha_cierre.isoformat() if ciclo.fecha_cierre else None,
            'salario_ciclo': str(ciclo.salario_ciclo),
            'estado': ciclo.estado,
            'sobrante_transferido': str(ciclo.sobrante_transferido),
        })
    return ciclos


def _serialize_gastos_fijos(user):
    gastos = []
    for gasto in GastoFijoPlantilla.objects.filter(usuario=user):
        gastos.append({
            'descripcion': gasto.descripcion,
            'monto': str(gasto.monto),
            'categoria_nombre': gasto.categoria.nombre if gasto.categoria else None,
            'frecuencia': gasto.frecuencia,
            'activa': gasto.activa,
            'fecha_ultima_aplicacion': gasto.fecha_ultima_aplicacion.isoformat() if gasto.fecha_ultima_aplicacion else None,
        })
    return gastos


def _serialize_eventos(user):
    eventos = []
    for evento in EventoCalendario.objects.filter(usuario=user):
        eventos.append({
            'titulo': evento.titulo,
            'descripcion': evento.descripcion,
            'fecha': evento.fecha.isoformat(),
            'tipo': evento.tipo,
            'monto': str(evento.monto) if evento.monto else None,
            'repetir_anualmente': evento.repetir_anualmente,
            'completado': evento.completado,
        })
    return eventos


def _serialize_fondo_ahorro(user):
    try:
        fondo = FondoAhorro.objects.get(usuario=user)
        return {
            'saldo_disponible': str(fondo.saldo_disponible),
        }
    except FondoAhorro.DoesNotExist:
        return None


def _serialize_inversiones(user):
    inversiones = []
    for inv in Inversion.objects.filter(usuario=user):
        inversiones.append({
            'nombre': inv.nombre,
            'monto_inicial': str(inv.monto_inicial),
            'monto_final': str(inv.monto_final) if inv.monto_final else None,
            'rendimiento_esperado': str(inv.rendimiento_esperado) if inv.rendimiento_esperado else None,
            'tipo_activo': inv.tipo_activo,
            'fecha_inicio': inv.fecha_inicio.isoformat() if inv.fecha_inicio else None,
            'fecha_vencimiento': inv.fecha_vencimiento.isoformat() if inv.fecha_vencimiento else None,
            'estado': inv.estado,
            'notas': inv.notas,
        })
    return inversiones


def _serialize_metas_ahorro(user):
    metas = []
    for meta in MetaAhorro.objects.filter(usuario=user):
        metas.append({
            'nombre': meta.nombre,
            'monto_objetivo': str(meta.monto_objetivo),
            'saldo_actual': str(meta.saldo_actual),
            'icono': meta.icono,
            'color': meta.color,
            'fecha_objetivo': meta.fecha_objetivo.isoformat() if meta.fecha_objetivo else None,
            'completada': meta.completada,
        })
    return metas


def _serialize_movimientos_patrimonio(user):
    movimientos = []
    for mov in MovimientoPatrimonio.objects.filter(usuario=user):
        movimientos.append({
            'tipo': mov.tipo,
            'monto': str(mov.monto),
            'descripcion': mov.descripcion,
            'fecha': mov.fecha.isoformat(),
        })
    return movimientos


def _serialize_widgets_config(user):
    try:
        config = WidgetConfiguracion.objects.get(usuario=user)
        return {
            'widgets_activos': config.widgets_activos,
        }
    except WidgetConfiguracion.DoesNotExist:
        return None


# Funciones auxiliares para restauración
def _restore_configuracion(user, config_data):
    if not config_data:
        return
    
    from decimal import Decimal
    config, created = ConfiguracionUsuario.objects.get_or_create(
        usuario=user,
        defaults={
            'salario_base': Decimal(config_data['salario_base']),
            'dia_corte': config_data['dia_corte'],
            'dias_plazo_tolerancia': config_data['dias_plazo_tolerancia'],
            'moneda': config_data['moneda'],
            'configurado': config_data['configurado'],
            'ha_visto_tutorial': config_data['ha_visto_tutorial'],
        }
    )
    
    if not created:
        config.salario_base = Decimal(config_data['salario_base'])
        config.dia_corte = config_data['dia_corte']
        config.dias_plazo_tolerancia = config_data['dias_plazo_tolerancia']
        config.moneda = config_data['moneda']
        config.configurado = config_data['configurado']
        config.ha_visto_tutorial = config_data['ha_visto_tutorial']
        config.save()


def _restore_categorias(user, categorias_data):
    from decimal import Decimal
    for cat_data in categorias_data:
        defaults = {
            'color': cat_data['color'],
        }
        # Solo agregar presupuesto_mensual si existe en los datos
        if 'presupuesto_mensual' in cat_data:
            defaults['presupuesto_mensual'] = Decimal(cat_data['presupuesto_mensual'])
        
        Categoria.objects.get_or_create(
            usuario=user,
            nombre=cat_data['nombre'],
            defaults=defaults
        )


def _restore_gastos_fijos(user, gastos_data):
    from decimal import Decimal
    for gasto_data in gastos_data:
        categoria = None
        if gasto_data.get('categoria_nombre'):
            try:
                categoria = Categoria.objects.get(usuario=user, nombre=gasto_data['categoria_nombre'])
            except Categoria.DoesNotExist:
                pass
        
        GastoFijoPlantilla.objects.get_or_create(
            usuario=user,
            descripcion=gasto_data['descripcion'],
            defaults={
                'monto': Decimal(gasto_data['monto']),
                'categoria': categoria,
                'frecuencia': gasto_data['frecuencia'],
                'activa': gasto_data['activa'],
            }
        )


def _restore_eventos(user, eventos_data):
    from decimal import Decimal
    for evento_data in eventos_data:
        EventoCalendario.objects.get_or_create(
            usuario=user,
            titulo=evento_data['titulo'],
            fecha=datetime.fromisoformat(evento_data['fecha']).date(),
            defaults={
                'descripcion': evento_data.get('descripcion', ''),
                'tipo': evento_data['tipo'],
                'monto': Decimal(evento_data['monto']) if evento_data.get('monto') else None,
                'repetir_anualmente': evento_data['repetir_anualmente'],
                'completado': evento_data['completado'],
            }
        )


def _restore_metas_ahorro(user, metas_data):
    from decimal import Decimal
    for meta_data in metas_data:
        MetaAhorro.objects.get_or_create(
            usuario=user,
            nombre=meta_data['nombre'],
            defaults={
                'monto_objetivo': Decimal(meta_data['monto_objetivo']),
                'saldo_actual': Decimal(meta_data['saldo_actual']),
                'icono': meta_data['icono'],
                'color': meta_data.get('color', '#10B981'),
                'fecha_objetivo': datetime.fromisoformat(meta_data['fecha_objetivo']).date() if meta_data.get('fecha_objetivo') else None,
                'completada': meta_data.get('completada', False),
            }
        )


def _restore_widgets_config(user, widgets_data):
    if not widgets_data:
        return
    
    config, created = WidgetConfiguracion.objects.get_or_create(usuario=user)
    config.widgets_activos = widgets_data.get('widgets_activos', [])
    config.save()




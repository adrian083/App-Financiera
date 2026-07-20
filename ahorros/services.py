"""Servicios de negocio del módulo de ahorros e inversiones."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from ahorros.models import FondoAhorro, Inversion, MovimientoPatrimonio
from presupuesto.models import CicloMensual, Movimiento


def _registrar_movimiento(usuario, fondo, tipo, monto, descripcion, **kwargs):
    return MovimientoPatrimonio.objects.create(
        usuario=usuario,
        fondo=fondo,
        tipo=tipo,
        monto=monto,
        descripcion=descripcion,
        **kwargs,
    )


@transaction.atomic
def registrar_envio_desde_presupuesto(usuario, movimiento: Movimiento):
    fondo = FondoAhorro.obtener(usuario)
    fondo.saldo_disponible += movimiento.monto
    fondo.save()
    _registrar_movimiento(
        usuario, fondo,
        MovimientoPatrimonio.ENTRADA_DERIVACION,
        movimiento.monto,
        f'Derivación: {movimiento.descripcion}',
        movimiento_presupuesto=movimiento,
        ciclo=movimiento.ciclo,
    )


@transaction.atomic
def registrar_entrada_sobrante(usuario, ciclo, monto: Decimal):
    fondo = FondoAhorro.obtener(usuario)
    fondo.saldo_disponible += monto
    fondo.save()
    _registrar_movimiento(
        usuario, fondo,
        MovimientoPatrimonio.ENTRADA_SOBRANTE,
        monto,
        f'Sobrante del ciclo {ciclo.etiqueta}',
        ciclo=ciclo,
    )


@transaction.atomic
def retirar_ahorro(usuario, monto: Decimal, descripcion: str, ciclo: CicloMensual):
    fondo = FondoAhorro.obtener(usuario)
    if fondo.saldo_disponible < monto:
        raise ValueError('Saldo insuficiente en el fondo de ahorro.')

    fondo.saldo_disponible -= monto
    fondo.save()

    movimiento = Movimiento.objects.create(
        usuario=usuario,
        ciclo=ciclo,
        tipo=Movimiento.INYECCION_AHORRO,
        monto=monto,
        descripcion=descripcion or 'Retiro de ahorro',
    )

    _registrar_movimiento(
        usuario, fondo,
        MovimientoPatrimonio.RETIRO,
        monto,
        descripcion or 'Retiro hacia gastos del ciclo',
        movimiento_presupuesto=movimiento,
        ciclo=ciclo,
    )
    return movimiento


@transaction.atomic
def crear_inversion(usuario, nombre, monto, fecha_vencimiento, notas=''):
    fondo = FondoAhorro.obtener(usuario)
    if fondo.saldo_disponible < monto:
        raise ValueError('Saldo insuficiente para invertir.')

    fondo.saldo_disponible -= monto
    fondo.save()

    inversion = Inversion.objects.create(
        usuario=usuario,
        nombre=nombre,
        monto_inicial=monto,
        fecha_vencimiento=fecha_vencimiento,
        notas=notas,
    )

    _registrar_movimiento(
        usuario, fondo,
        MovimientoPatrimonio.INVERSION_SALIDA,
        monto,
        f'Inversión: {nombre}',
        inversion=inversion,
    )
    return inversion


@transaction.atomic
def cerrar_inversion(usuario, inversion: Inversion, monto_final: Decimal, extender=False, nueva_fecha=None):
    fondo = FondoAhorro.obtener(usuario)

    if extender and nueva_fecha:
        inversion.fecha_vencimiento = nueva_fecha
        inversion.estado = Inversion.EN_CURSO
        inversion.save()
        return inversion

    inversion.monto_final = monto_final
    inversion.fecha_cierre = timezone.now()

    fondo.saldo_disponible += monto_final
    fondo.save()

    _registrar_movimiento(
        usuario, fondo,
        MovimientoPatrimonio.INVERSION_RETORNO,
        monto_final,
        f'Retorno de inversión: {inversion.nombre}',
        inversion=inversion,
    )

    diff = monto_final - inversion.monto_inicial
    if diff > 0:
        inversion.estado = Inversion.CERRADA_GANANCIA
        _registrar_movimiento(
            usuario, fondo,
            MovimientoPatrimonio.GANANCIA,
            diff,
            f'Ganancia en {inversion.nombre}',
            inversion=inversion,
        )
    elif diff < 0:
        inversion.estado = Inversion.CERRADA_PERDIDA
        _registrar_movimiento(
            usuario, fondo,
            MovimientoPatrimonio.PERDIDA_CAPITAL,
            abs(diff),
            f'Pérdida de capital en {inversion.nombre}',
            inversion=inversion,
        )
    else:
        inversion.estado = Inversion.CERRADA_NEUTRAL

    inversion.save()
    return inversion


def marcar_inversiones_vencidas(usuario):
    hoy = timezone.now().date()
    Inversion.objects.filter(
        usuario=usuario,
        estado__in=[Inversion.ACTIVA, Inversion.EN_CURSO],
        fecha_vencimiento__lte=hoy,
    ).update(estado=Inversion.VENCIDA_PENDIENTE)


def inversiones_pendientes_cierre(usuario):
    marcar_inversiones_vencidas(usuario)
    return Inversion.objects.filter(usuario=usuario, estado=Inversion.VENCIDA_PENDIENTE)


def inversiones_proximas_vencer(usuario, dias=7):
    hoy = timezone.now().date()
    limite = hoy + timedelta(days=dias)
    return Inversion.objects.filter(
        usuario=usuario,
        estado__in=[Inversion.ACTIVA, Inversion.EN_CURSO],
        fecha_vencimiento__gt=hoy,
        fecha_vencimiento__lte=limite,
    ).order_by('fecha_vencimiento')

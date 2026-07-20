from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class FondoAhorro(models.Model):
    """Saldo disponible del fondo de ahorro por usuario."""

    usuario = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='fondo_ahorro',
    )
    saldo_disponible = models.DecimalField(
        max_digits=14, decimal_places=0, default=Decimal('0'),
    )
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Fondo de ahorro'
        verbose_name_plural = 'Fondos de ahorro'

    @classmethod
    def obtener(cls, usuario):
        obj, _ = cls.objects.get_or_create(usuario=usuario)
        return obj


class MovimientoPatrimonio(models.Model):
    ENTRADA_DERIVACION = 'entrada_derivacion'
    ENTRADA_SOBRANTE = 'entrada_sobrante'
    RETIRO = 'retiro'
    INVERSION_SALIDA = 'inversion_salida'
    INVERSION_RETORNO = 'inversion_retorno'
    GANANCIA = 'ganancia'
    PERDIDA_CAPITAL = 'perdida_capital'

    TIPOS = [
        (ENTRADA_DERIVACION, 'Entrada por derivación'),
        (ENTRADA_SOBRANTE, 'Entrada por sobrante de ciclo'),
        (RETIRO, 'Retiro de ahorro'),
        (INVERSION_SALIDA, 'Salida a inversión'),
        (INVERSION_RETORNO, 'Retorno de inversión'),
        (GANANCIA, 'Ganancia de inversión'),
        (PERDIDA_CAPITAL, 'Pérdida de capital'),
    ]

    usuario = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='movimientos_patrimonio',
    )
    tipo = models.CharField(max_length=30, choices=TIPOS)
    monto = models.DecimalField(max_digits=14, decimal_places=0)
    descripcion = models.CharField(max_length=300)
    fondo = models.ForeignKey(
        FondoAhorro, on_delete=models.CASCADE, related_name='movimientos',
    )
    inversion = models.ForeignKey(
        'Inversion', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='movimientos_patrimonio',
    )
    ciclo = models.ForeignKey(
        'presupuesto.CicloMensual', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='movimientos_patrimonio',
    )
    movimiento_presupuesto = models.ForeignKey(
        'presupuesto.Movimiento', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='movimientos_patrimonio',
    )
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Movimiento de patrimonio'
        verbose_name_plural = 'Movimientos de patrimonio'

    def __str__(self):
        return f'{self.get_tipo_display()}: {self.descripcion}'


class Inversion(models.Model):
    ACTIVA = 'activa'
    VENCIDA_PENDIENTE = 'vencida'
    CERRADA_GANANCIA = 'ganancia'
    CERRADA_PERDIDA = 'perdida'
    CERRADA_NEUTRAL = 'neutral'
    EN_CURSO = 'en_curso'

    ESTADOS = [
        (ACTIVA, 'Activa'),
        (VENCIDA_PENDIENTE, 'Vencida (pendiente cierre)'),
        (CERRADA_GANANCIA, 'Cerrada con ganancia'),
        (CERRADA_PERDIDA, 'Cerrada con pérdida'),
        (CERRADA_NEUTRAL, 'Cerrada sin cambio'),
        (EN_CURSO, 'En curso (plazo extendido)'),
    ]

    usuario = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='inversiones',
    )
    nombre = models.CharField(max_length=200)
    monto_inicial = models.DecimalField(max_digits=14, decimal_places=0)
    monto_final = models.DecimalField(
        max_digits=14, decimal_places=0, null=True, blank=True,
    )
    fecha_inicio = models.DateField(default=date.today)
    fecha_vencimiento = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default=ACTIVA)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    notas = models.TextField(blank=True)

    class Meta:
        ordering = ['-fecha_inicio']
        verbose_name = 'Inversión'
        verbose_name_plural = 'Inversiones'

    def __str__(self):
        return f'{self.nombre} ({self.monto_inicial})'

    @property
    def esta_vencida(self):
        hoy = timezone.now().date()
        return hoy >= self.fecha_vencimiento and self.estado in (
            self.ACTIVA, self.EN_CURSO, self.VENCIDA_PENDIENTE,
        )

    @property
    def proxima_a_vencer(self):
        hoy = timezone.now().date()
        limite = hoy + timedelta(days=7)
        return (
            self.estado in (self.ACTIVA, self.EN_CURSO)
            and hoy <= self.fecha_vencimiento <= limite
        )

    @property
    def resultado(self):
        if self.monto_final is None:
            return None
        return self.monto_final - self.monto_inicial

    @classmethod
    def total_ganancias(cls, usuario):
        total = Decimal('0')
        for inv in cls.objects.filter(
            usuario=usuario, estado=cls.CERRADA_GANANCIA, monto_final__isnull=False,
        ):
            total += inv.monto_final - inv.monto_inicial
        return total

    @classmethod
    def total_perdidas(cls, usuario):
        total = Decimal('0')
        for inv in cls.objects.filter(
            usuario=usuario, estado=cls.CERRADA_PERDIDA, monto_final__isnull=False,
        ):
            total += inv.monto_inicial - inv.monto_final
        return total

    @classmethod
    def monto_congelado(cls, usuario):
        return cls.objects.filter(
            usuario=usuario,
            estado__in=[cls.ACTIVA, cls.EN_CURSO, cls.VENCIDA_PENDIENTE],
        ).aggregate(t=Sum('monto_inicial'))['t'] or Decimal('0')

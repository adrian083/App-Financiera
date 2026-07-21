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

    ACCIONES = 'acciones'
    CRIPTO = 'cripto'
    FONDOS = 'fondos'
    INMOBILIARIO = 'inmobiliario'
    RENTA_FIJA = 'renta_fija'
    OTRO = 'otro'

    TIPOS_ACTIVO = [
        (ACCIONES, 'Acciones'),
        (CRIPTO, 'Criptomonedas'),
        (FONDOS, 'Fondos indexados'),
        (INMOBILIARIO, 'Bienes raíces'),
        (RENTA_FIJA, 'Renta fija / CDT'),
        (OTRO, 'Otro'),
    ]

    # color + icono para visualización de portafolio
    META_ACTIVO = {
        ACCIONES: {'color': '#06B6D4', 'icono': 'fa-arrow-trend-up'},
        CRIPTO: {'color': '#F59E0B', 'icono': 'fa-bitcoin-sign'},
        FONDOS: {'color': '#8B5CF6', 'icono': 'fa-layer-group'},
        INMOBILIARIO: {'color': '#10B981', 'icono': 'fa-building'},
        RENTA_FIJA: {'color': '#3B82F6', 'icono': 'fa-landmark'},
        OTRO: {'color': '#94A3B8', 'icono': 'fa-coins'},
    }

    usuario = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='inversiones',
    )
    nombre = models.CharField(max_length=200)
    tipo_activo = models.CharField(
        max_length=20, choices=TIPOS_ACTIVO, default=OTRO,
        verbose_name='Tipo de activo',
    )
    rendimiento_esperado = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        verbose_name='Rendimiento esperado (% anual)',
    )
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

    @property
    def roi(self):
        """Retorno sobre la inversión en porcentaje (cerradas)."""
        if self.monto_final is None or self.monto_inicial == 0:
            return None
        return (self.monto_final - self.monto_inicial) / self.monto_inicial * 100

    @property
    def rendimiento_proyectado(self):
        """Ganancia proyectada en dinero según el rendimiento esperado."""
        if not self.rendimiento_esperado:
            return None
        return (self.monto_inicial * self.rendimiento_esperado / 100).quantize(Decimal('1'))

    @property
    def color_activo(self):
        return self.META_ACTIVO.get(self.tipo_activo, self.META_ACTIVO[self.OTRO])['color']

    @property
    def icono_activo(self):
        return self.META_ACTIVO.get(self.tipo_activo, self.META_ACTIVO[self.OTRO])['icono']

    @property
    def esta_abierta(self):
        return self.estado in (self.ACTIVA, self.EN_CURSO, self.VENCIDA_PENDIENTE)

    @classmethod
    def distribucion_portafolio(cls, usuario):
        """Distribución del capital abierto por tipo de activo."""
        abiertas = cls.objects.filter(
            usuario=usuario,
            estado__in=[cls.ACTIVA, cls.EN_CURSO, cls.VENCIDA_PENDIENTE],
        )
        agrupado = {}
        for inv in abiertas:
            meta = cls.META_ACTIVO.get(inv.tipo_activo, cls.META_ACTIVO[cls.OTRO])
            key = inv.get_tipo_activo_display()
            if key not in agrupado:
                agrupado[key] = {'total': Decimal('0'), 'color': meta['color'], 'icono': meta['icono']}
            agrupado[key]['total'] += inv.monto_inicial
        return [
            {'nombre': k, 'total': v['total'], 'color': v['color'], 'icono': v['icono']}
            for k, v in sorted(agrupado.items(), key=lambda x: -x[1]['total'])
        ]

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

    @classmethod
    def capital_invertido(cls, usuario):
        return cls.monto_congelado(usuario)


class MetaAhorro(models.Model):
    """Objetivo de ahorro a corto/mediano plazo (fondo de emergencia, viaje, etc.)."""

    ICONOS = [
        ('fa-shield-halved', 'Fondo de emergencia'),
        ('fa-umbrella-beach', 'Vacaciones / Viaje'),
        ('fa-laptop', 'Tecnología'),
        ('fa-car', 'Vehículo'),
        ('fa-house', 'Vivienda / Hogar'),
        ('fa-graduation-cap', 'Educación'),
        ('fa-gift', 'Regalo / Evento'),
        ('fa-piggy-bank', 'General'),
    ]

    usuario = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='metas_ahorro',
    )
    nombre = models.CharField(max_length=120)
    icono = models.CharField(max_length=40, choices=ICONOS, default='fa-piggy-bank')
    color = models.CharField(max_length=7, default='#10B981')
    monto_objetivo = models.DecimalField(max_digits=14, decimal_places=0)
    saldo_actual = models.DecimalField(
        max_digits=14, decimal_places=0, default=Decimal('0'),
    )
    fecha_objetivo = models.DateField(null=True, blank=True)
    completada = models.BooleanField(default=False)
    creada = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['completada', '-creada']
        verbose_name = 'Meta de ahorro'
        verbose_name_plural = 'Metas de ahorro'

    def __str__(self):
        return f'{self.nombre} ({self.saldo_actual}/{self.monto_objetivo})'

    @property
    def progreso(self):
        if self.monto_objetivo <= 0:
            return 0
        pct = int(self.saldo_actual / self.monto_objetivo * 100)
        return min(pct, 100)

    @property
    def restante(self):
        return max(self.monto_objetivo - self.saldo_actual, Decimal('0'))

    @property
    def dias_restantes(self):
        if not self.fecha_objetivo:
            return None
        return (self.fecha_objetivo - timezone.now().date()).days

    @classmethod
    def total_ahorrado(cls, usuario):
        return cls.objects.filter(usuario=usuario).aggregate(
            t=Sum('saldo_actual'))['t'] or Decimal('0')

    @classmethod
    def total_objetivo(cls, usuario):
        return cls.objects.filter(usuario=usuario).aggregate(
            t=Sum('monto_objetivo'))['t'] or Decimal('0')


class DepositoMeta(models.Model):
    """Historial de aportes a una meta de ahorro."""

    meta = models.ForeignKey(
        MetaAhorro, on_delete=models.CASCADE, related_name='depositos',
    )
    monto = models.DecimalField(max_digits=14, decimal_places=0)
    nota = models.CharField(max_length=200, blank=True)
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f'Aporte {self.monto} a {self.meta.nombre}'

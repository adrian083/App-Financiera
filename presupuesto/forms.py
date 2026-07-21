from django import forms

from core.currency import moneda_choices
from core.form_styles import FORM_INPUT, FORM_INPUT_COP, FORM_INPUT_LG, FORM_INPUT_SM
from core.utils.moneda import parse_cop
from presupuesto.models import (
    Categoria,
    ConfiguracionUsuario,
    GastoFijoPlantilla,
)


class MontoCOPField(forms.CharField):
    def to_python(self, value):
        if value in self.empty_values:
            return None
        return parse_cop(value)


class ConfiguracionForm(forms.ModelForm):
    salario_base = MontoCOPField(
        label='Salario base mensual',
        widget=forms.TextInput(attrs={
            'class': FORM_INPUT_COP,
            'placeholder': '$ 0',
            'data-cop': 'true',
        }),
    )
    moneda = forms.ChoiceField(
        label='Moneda de visualización',
        choices=moneda_choices(),
        widget=forms.Select(attrs={'class': FORM_INPUT}),
    )

    class Meta:
        model = ConfiguracionUsuario
        fields = ['salario_base', 'moneda', 'dia_corte', 'dias_plazo_tolerancia']
        widgets = {
            'dia_corte': forms.NumberInput(attrs={
                'class': FORM_INPUT,
                'min': 1, 'max': 31,
            }),
            'dias_plazo_tolerancia': forms.NumberInput(attrs={
                'class': FORM_INPUT,
                'min': 0, 'max': 15,
            }),
        }
        labels = {
            'dia_corte': 'Día de corte/pago',
            'dias_plazo_tolerancia': 'Días de plazo/tolerancia',
        }
        help_texts = {
            'moneda': 'Solo cambia el símbolo mostrado; no convierte los montos guardados.',
            'dias_plazo_tolerancia': 'Días extra para confirmar pago cuando el día de corte cae en fin de semana o festivo.',
        }


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'color', 'activa']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': FORM_INPUT}),
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'h-10 w-16 rounded border border-slate-300 dark:border-slate-600'}),
            'activa': forms.CheckboxInput(attrs={'class': 'rounded border-slate-300 dark:border-slate-600'}),
        }


class MovimientoForm(forms.Form):
    monto = MontoCOPField(
        label='Monto',
        widget=forms.TextInput(attrs={'class': FORM_INPUT_COP, 'data-cop': 'true'}),
    )
    descripcion = forms.CharField(
        label='Descripción',
        max_length=300,
        widget=forms.TextInput(attrs={'class': FORM_INPUT}),
    )
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.none(),
        required=False,
        label='Categoría',
        widget=forms.Select(attrs={'class': FORM_INPUT, 'id': 'id_categoria'}),
    )
    es_gasto_fijo = forms.BooleanField(
        required=False,
        label='Guardar como gasto fijo (plantilla)',
        widget=forms.CheckboxInput(attrs={'class': 'rounded border-slate-300 dark:border-slate-600'}),
    )

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        if usuario:
            self.fields['categoria'].queryset = Categoria.objects.filter(
                usuario=usuario, activa=True,
            )


class EnvioAhorroForm(forms.Form):
    monto = MontoCOPField(
        label='Monto',
        widget=forms.TextInput(attrs={'class': FORM_INPUT_COP, 'data-cop': 'true'}),
    )
    descripcion = forms.CharField(
        label='Descripción',
        max_length=300,
        widget=forms.TextInput(attrs={'class': FORM_INPUT}),
    )


class IngresoForm(forms.Form):
    monto = MontoCOPField(
        label='Monto',
        widget=forms.TextInput(attrs={'class': FORM_INPUT_COP, 'data-cop': 'true'}),
    )
    descripcion = forms.CharField(
        label='Descripción',
        max_length=300,
        widget=forms.TextInput(attrs={'class': FORM_INPUT}),
    )


class GastoFijoPlantillaForm(forms.ModelForm):
    monto = MontoCOPField(
        label='Monto mensual',
        widget=forms.TextInput(attrs={'class': FORM_INPUT_COP, 'data-cop': 'true'}),
    )

    class Meta:
        model = GastoFijoPlantilla
        fields = ['descripcion', 'monto', 'categoria', 'activa']
        widgets = {
            'descripcion': forms.TextInput(attrs={'class': FORM_INPUT}),
            'categoria': forms.Select(attrs={'class': FORM_INPUT}),
            'activa': forms.CheckboxInput(attrs={'class': 'rounded border-slate-300 dark:border-slate-600'}),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        if usuario:
            self.fields['categoria'].queryset = Categoria.objects.filter(usuario=usuario, activa=True)


class CierreCicloForm(forms.Form):
    nuevo_salario = MontoCOPField(
        label='Salario para el nuevo ciclo',
        widget=forms.TextInput(attrs={'class': FORM_INPUT_COP, 'data-cop': 'true'}),
    )


class ConfirmarGastoFijoForm(forms.Form):
    movimiento_id = forms.IntegerField(widget=forms.HiddenInput())
    monto = MontoCOPField(
        widget=forms.TextInput(attrs={
            'class': f'{FORM_INPUT_SM} w-40',
            'data-cop': 'true',
        }),
    )

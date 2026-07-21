from django import forms

from ahorros.models import MetaAhorro
from core.form_styles import FORM_INPUT, FORM_INPUT_COP
from core.utils.moneda import parse_cop


class MontoCOPField(forms.CharField):
    def to_python(self, value):
        if value in self.empty_values:
            return None
        return parse_cop(value)


class RetiroAhorroForm(forms.Form):
    monto = MontoCOPField(
        label='Monto a retirar',
        widget=forms.TextInput(attrs={'class': FORM_INPUT_COP, 'data-cop': 'true'}),
    )
    descripcion = forms.CharField(
        label='Descripción',
        max_length=300,
        required=False,
        widget=forms.TextInput(attrs={
            'class': FORM_INPUT,
            'placeholder': 'Ej: Cubrir gasto médico',
        }),
    )


class InversionForm(forms.Form):
    nombre = forms.CharField(
        label='Nombre / descripción',
        max_length=200,
        widget=forms.TextInput(attrs={'class': FORM_INPUT}),
    )
    monto = MontoCOPField(
        label='Monto a invertir',
        widget=forms.TextInput(attrs={'class': FORM_INPUT_COP, 'data-cop': 'true'}),
    )
    fecha_vencimiento = forms.DateField(
        label='Fecha de vencimiento',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': FORM_INPUT,
            'id': 'id_fecha_vencimiento',
        }),
    )
    notas = forms.CharField(
        required=False,
        label='Notas',
        widget=forms.Textarea(attrs={'class': FORM_INPUT, 'rows': 2}),
    )


class CierreInversionForm(forms.Form):
    monto_final = MontoCOPField(
        label='Monto final recuperado',
        widget=forms.TextInput(attrs={'class': FORM_INPUT_COP, 'data-cop': 'true'}),
    )
    extender = forms.BooleanField(
        required=False,
        label='Sigue en curso (extender plazo)',
        widget=forms.CheckboxInput(attrs={'class': 'rounded border-slate-300 dark:border-slate-600', 'id': 'id_extender'}),
    )
    nueva_fecha = forms.DateField(
        required=False,
        label='Nueva fecha de vencimiento',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': FORM_INPUT,
            'id': 'id_nueva_fecha',
        }),
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('extender') and not cleaned.get('nueva_fecha'):
            self.add_error('nueva_fecha', 'Indica la nueva fecha de vencimiento.')
        if not cleaned.get('extender') and cleaned.get('monto_final') is None:
            self.add_error('monto_final', 'Indica el monto final recuperado.')
        return cleaned


class MetaAhorroForm(forms.ModelForm):
    monto_objetivo = MontoCOPField(
        label='Monto objetivo',
        widget=forms.TextInput(attrs={'class': FORM_INPUT_COP, 'data-cop': 'true'}),
    )

    class Meta:
        model = MetaAhorro
        fields = ['nombre', 'icono', 'color', 'monto_objetivo', 'fecha_objetivo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': FORM_INPUT}),
            'icono': forms.Select(attrs={'class': FORM_INPUT}),
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'h-10 w-16 rounded border border-slate-300 dark:border-slate-600'}),
            'fecha_objetivo': forms.DateInput(attrs={'type': 'date', 'class': FORM_INPUT}),
        }

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from core.form_styles import FORM_INPUT, FORM_INPUT_COP, FORM_INPUT_LG
from core.utils.moneda import parse_cop
from presupuesto.models import ConfiguracionUsuario


class RegistroForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': FORM_INPUT_LG,
            'placeholder': 'correo@ejemplo.com',
        }),
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': FORM_INPUT_LG,
                'placeholder': 'Nombre de usuario',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('password1', 'password2'):
            self.fields[name].widget.attrs.update({'class': FORM_INPUT_LG})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': FORM_INPUT_LG})


class ConfiguracionInicialForm(forms.ModelForm):
    salario_base = forms.CharField(
        label='Salario base mensual',
        widget=forms.TextInput(attrs={
            'class': FORM_INPUT_COP,
            'data-cop': 'true',
            'placeholder': '$ 0',
        }),
    )

    class Meta:
        model = ConfiguracionUsuario
        fields = ['salario_base', 'dia_corte']
        widgets = {
            'dia_corte': forms.NumberInput(attrs={
                'class': FORM_INPUT,
                'min': 1, 'max': 31,
            }),
        }

    def clean_salario_base(self):
        return parse_cop(self.cleaned_data['salario_base'])

from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from core.forms import LoginForm, RegistroForm
from presupuesto.utils import seed_categorias_usuario


class FinanzasLoginView(LoginView):
    template_name = 'registration/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


class FinanzasLogoutView(LogoutView):
    next_page = reverse_lazy('login')


def registro(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            seed_categorias_usuario(user)
            login(request, user)
            return redirect('configuracion_inicial')
    else:
        form = RegistroForm()
    return render(request, 'registration/register.html', {'form': form})

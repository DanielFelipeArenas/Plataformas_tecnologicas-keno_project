from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Jugador, Sala
import random
import string

def index(request):
    return render(request, "index.html")

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # Buscar usuario por email
        try:
            user = User.objects.get(email=email)
            user = authenticate(request, username=user.username, password=password)
            
            if user is not None:
                login(request, user)
                return redirect('sala')
            else:
                messages.error(request, 'Contraseña incorrecta')
        except User.DoesNotExist:
            messages.error(request, 'Email no registrado')
    
    return render(request, "login.html")

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # Validaciones básicas
        if User.objects.filter(username=username).exists():
            messages.error(request, 'El nombre de usuario ya existe')
            return render(request, "register.html")
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'El email ya está registrado')
            return render(request, "register.html")
        
        # Crear usuario
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        
        # Crear perfil de jugador
        Jugador.objects.create(
            user=user,
            nickname=username
        )
        
        # Auto-login después del registro
        login(request, user)
        messages.success(request, '¡Registro exitoso!')
        return redirect('sala')
    
    return render(request, "register.html")

@login_required
def sala(request):
    jugador = Jugador.objects.get(user=request.user)
    
    # Crear o buscar sala activa
    sala_activa = Sala.objects.filter(activa=True, jugadores__lt=10).first()
    
    if not sala_activa:
        # Crear nueva sala
        codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        sala_activa = Sala.objects.create(
            codigo=codigo,
            creador=jugador
        )
    
    # Agregar jugador a la sala si no está
    if jugador not in sala_activa.jugadores.all():
        sala_activa.jugadores.add(jugador)
    
    context = {
        'jugador': jugador,
        'sala': sala_activa,
        'url_invitacion': request.build_absolute_uri() + f"?sala={sala_activa.codigo}"
    }
    
    return render(request, "sala.html", context)

@login_required
def inicio(request):
    return render(request, "inicio.html")

def logout_view(request):
    logout(request)
    return redirect('index')
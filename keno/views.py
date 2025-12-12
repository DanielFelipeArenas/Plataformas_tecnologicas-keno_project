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
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        
        if not email or not password:
            messages.error(request, 'Por favor completa todos los campos')
            return render(request, "login.html")
        
        try:
            user_obj = User.objects.get(email=email)
            user = authenticate(request, username=user_obj.username, password=password)
            
            if user is not None:
                login(request, user)
                return redirect('sala')
            else:
                messages.error(request, 'Contraseña incorrecta')
        except User.DoesNotExist:
            messages.error(request, 'Email no registrado')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return render(request, "login.html")

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        
        if not username or not email or not password:
            messages.error(request, 'Por favor completa todos los campos')
            return render(request, "register.html")
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'El nombre de usuario ya existe')
            return render(request, "register.html")
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'El email ya está registrado')
            return render(request, "register.html")
        
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            Jugador.objects.create(
                user=user,
                nickname=username
            )
            
            login(request, user)
            messages.success(request, '¡Registro exitoso!')
            return redirect('sala')
            
        except Exception as e:
            messages.error(request, f'Error al crear usuario: {str(e)}')
            return render(request, "register.html")
    
    return render(request, "register.html")

@login_required
def sala(request):
    try:
        # Obtener o crear jugador
        jugador, created = Jugador.objects.get_or_create(
            user=request.user,
            defaults={'nickname': request.user.username}
        )
        
        # Buscar UNA sala activa (siempre la misma para todos)
        sala_activa = Sala.objects.filter(activa=True).first()
        
        if not sala_activa:
            # Solo crear sala si NO existe ninguna
            codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            sala_activa = Sala.objects.create(
                codigo=codigo,
                creador=jugador
            )
        
        # Agregar jugador SOLO si no está ya en la sala
        if not sala_activa.jugadores.filter(id=jugador.id).exists():
            sala_activa.jugadores.add(jugador)
        
        # Obtener lista de jugadores ÚNICOS
        jugadores_en_sala = sala_activa.jugadores.all().distinct()
        
        context = {
            'jugador': jugador,
            'sala': sala_activa,
            'jugadores_lista': [j.nickname for j in jugadores_en_sala],
            'url_invitacion': request.build_absolute_uri().split('?')[0] + f"?sala={sala_activa.codigo}"
        }
        
        return render(request, "sala.html", context)
        
    except Exception as e:
        print(f"Error en sala: {e}")
        messages.error(request, f'Error: {str(e)}')
        return redirect('index')

@login_required
def inicio(request):
    return render(request, "inicio.html")

@login_required
def ranking(request):
    jugadores = Jugador.objects.all().order_by('-puntos_totales')
    
    for jugador in jugadores:
        if jugador.partidas_jugadas > 0:
            jugador.promedio = jugador.puntos_totales / jugador.partidas_jugadas
        else:
            jugador.promedio = 0
    
    context = {
        'ranking': jugadores
    }
    return render(request, "ranking.html", context)

def logout_view(request):
    logout(request)
    return redirect('index')
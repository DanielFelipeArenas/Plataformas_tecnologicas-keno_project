from django.db import models
from django.contrib.auth.models import User

class Jugador(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nickname = models.CharField(max_length=50, unique=True)
    puntos_totales = models.IntegerField(default=0)
    partidas_jugadas = models.IntegerField(default=0)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nickname

class Sala(models.Model):
    codigo = models.CharField(max_length=10, unique=True)
    creador = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='salas_creadas')
    jugadores = models.ManyToManyField(Jugador, related_name='salas')
    max_jugadores = models.IntegerField(default=10)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sala {self.codigo}"

class Partida(models.Model):
    sala = models.ForeignKey(Sala, on_delete=models.CASCADE)
    numeros_sorteados = models.JSONField(default=list)  # Lista de 20 números ganadores
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    finalizada = models.BooleanField(default=False)

    def __str__(self):
        return f"Partida {self.id} - Sala {self.sala.codigo}"

class Apuesta(models.Model):
    partida = models.ForeignKey(Partida, on_delete=models.CASCADE)
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE)
    numeros_elegidos = models.JSONField(default=list)  # Lista de hasta 20 números
    aciertos = models.IntegerField(default=0)
    puntos_ganados = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.jugador.nickname} - {self.aciertos} aciertos"
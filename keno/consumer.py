from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import json
import random

# ============================================================
#   CONSUMIDOR DE SALA (MANEJO DE TIEMPO Y JUGADORES)
# ============================================================

class SalaConsumer(AsyncWebsocketConsumer):
    tiempo_compartido = {}
    
    async def connect(self):
        self.sala_id = self.scope['url_route']['kwargs']['sala_id']
        self.room_group_name = f'sala_{self.sala_id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Inicializar tiempo por sala
        if self.sala_id not in SalaConsumer.tiempo_compartido:
            SalaConsumer.tiempo_compartido[self.sala_id] = 120
        
        players = await self.get_players_in_sala()
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'sala_update',
                'players': players,
                'tiempo': SalaConsumer.tiempo_compartido[self.sala_id]
            }
        )
    
    async def disconnect(self, close_code):
        from .models import Sala, Jugador

        try:
            user = self.scope["user"]

            # Si el usuario NO está autenticado, no hacemos nada
            if not user.is_authenticated:
                await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
                return
            
            # Obtener sala
            sala = await database_sync_to_async(Sala.objects.get)(id=self.sala_id)

            # Obtener jugador
            jugador = await database_sync_to_async(Jugador.objects.get)(user=user)

            # Remover jugador de la sala
            await database_sync_to_async(sala.jugadores.remove)(jugador)

            # Lista actualizada
            players = await self.get_players_in_sala()

            # Avisar a todos
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'sala_update',
                    'players': players,
                    'tiempo': SalaConsumer.tiempo_compartido.get(self.sala_id, 20)
                }
            )

            # Si la sala queda vacía → desactivarla
            if len(players) == 0:
                sala.activa = False
                await database_sync_to_async(sala.save)()

        except Exception as e:
            print("Error al desconectar jugador:", e)

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'player_joined':
            players = await self.get_players_in_sala()
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'sala_update',
                    'players': players,
                    'tiempo': SalaConsumer.tiempo_compartido.get(self.sala_id, 20)
                }
            )
        
        elif message_type == 'timer_update':
            tiempo = data.get('tiempo', 20)
            SalaConsumer.tiempo_compartido[self.sala_id] = tiempo
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'timer_sync',
                    'tiempo': tiempo
                }
            )
    
    async def sala_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'sala_update',
            'players': event['players'],
            'tiempo': event.get('tiempo', 20)
        }))
    
    async def timer_sync(self, event):
        await self.send(text_data=json.dumps({
            'type': 'timer_sync',
            'tiempo': event['tiempo']
        }))
    
    @database_sync_to_async
    def get_players_in_sala(self):
        from .models import Sala
        try:
            sala = Sala.objects.get(id=self.sala_id)
            return [jugador.nickname for jugador in sala.jugadores.all().distinct()]
        except:
            return []


# ============================================================
#   CONSUMIDOR DEL JUEGO KENO
# ============================================================

class GameConsumer(AsyncWebsocketConsumer):
    
    jugadores_listos = {}          # channel_name → {nickname, numeros}
    jugadores_confirmados = set()  # nicknames confirmados

    async def connect(self):
        self.game_group_name = 'game_room'
        
        await self.channel_layer.group_add(
            self.game_group_name,
            self.channel_name
        )
        await self.accept()

        await self.send(text_data=json.dumps({
            "type": "connected",
            "message": "Conexion establecida"
        }))
        
    async def disconnect(self, close_code):

        if self.channel_name in GameConsumer.jugadores_listos:
            nickname = GameConsumer.jugadores_listos[self.channel_name]['nickname']

            GameConsumer.jugadores_confirmados.discard(nickname)
            del GameConsumer.jugadores_listos[self.channel_name]
        
        await self.channel_layer.group_discard(
            self.game_group_name,
            self.channel_name
        )
        

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        # ----------------------------------------------------
        # 1. RECIBIR NUMEROS Y CONFIRMAR
        # ----------------------------------------------------
        if message_type == 'numeros_seleccionados':
            nickname = data.get('nickname')
            numeros = data.get('numeros', [])

            GameConsumer.jugadores_listos[self.channel_name] = {
                'nickname': nickname,
                'numeros': numeros
            }

            GameConsumer.jugadores_confirmados.add(nickname)

            total = len(GameConsumer.jugadores_listos)
            confirmados = len(GameConsumer.jugadores_confirmados)
            todos_listos = (confirmados == total and total > 0)

            await self.channel_layer.group_send(
                self.game_group_name,
                {
                    'type': 'estado_confirmaciones',
                    'confirmados': confirmados,
                    'total': total,
                    'todos_listos': todos_listos
                }
            )

            await self.send(text_data=json.dumps({
                'type': 'seleccion_confirmada',
                'message': f'Has seleccionado {len(numeros)} numeros'
            }))

        # ----------------------------------------------------
        # 2. INICIAR SORTEO — SOLO SI TODOS ESTÁN LISTOS
        # ----------------------------------------------------
        elif message_type == 'iniciar_sorteo':

            total = len(GameConsumer.jugadores_listos)
            confirmados = len(GameConsumer.jugadores_confirmados)

            if confirmados < total:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Faltan {total - confirmados} jugador(es) por confirmar'
                }))
                return
            
            numeros_ganadores = random.sample(range(1, 81), 20)
            
            resultados = []
            for channel, jugador_data in GameConsumer.jugadores_listos.items():
                nickname = jugador_data['nickname']
                numeros_jugador = jugador_data['numeros']
                
                aciertos = len(set(numeros_jugador) & set(numeros_ganadores))
                puntos = self.calcular_puntos(len(numeros_jugador), aciertos)
                
                resultados.append({
                    'nickname': nickname,
                    'aciertos': aciertos,
                    'puntos': puntos,
                    'numeros': numeros_jugador
                })
            
            resultados.sort(key=lambda x: x['puntos'], reverse=True)

            await self.guardar_partida(numeros_ganadores, resultados)

            GameConsumer.jugadores_confirmados.clear()

            await self.channel_layer.group_send(
                self.game_group_name,
                {
                    'type': 'sorteo_completado',
                    'numeros_ganadores': numeros_ganadores,
                    'resultados': resultados
                }
            )
    

    async def estado_confirmaciones(self, event):
        await self.send(text_data=json.dumps({
            'type': 'estado_confirmaciones',
            'confirmados': event['confirmados'],
            'total': event['total'],
            'todos_listos': event['todos_listos']
        }))

    async def sorteo_completado(self, event):
        await self.send(text_data=json.dumps({
            'type': 'sorteo_completado',
            'numeros_ganadores': event['numeros_ganadores'],
            'resultados': event['resultados']
        }))

    # -------------------------
    #  CALCULAR PUNTOS
    # -------------------------
    def calcular_puntos(self, numeros_seleccionados, aciertos):
        if numeros_seleccionados == 1:
            return 3 if aciertos == 1 else 0
        elif numeros_seleccionados == 2:
            return 15 if aciertos == 2 else 0
        elif numeros_seleccionados == 3:
            if aciertos == 3: return 45
            elif aciertos == 2: return 5
            else: return 0
        elif numeros_seleccionados == 4:
            if aciertos == 4: return 100
            elif aciertos == 3: return 10
            elif aciertos == 2: return 2
            else: return 0
        elif numeros_seleccionados == 5:
            if aciertos == 5: return 500
            elif aciertos == 4: return 50
            elif aciertos == 3: return 5
            else: return 0
        elif numeros_seleccionados <= 10:
            return aciertos * 50
        elif numeros_seleccionados <= 15:
            return aciertos * 100
        else:
            return aciertos * 150

    # -------------------------
    #  GUARDAR PARTIDA EN BD
    # -------------------------
    @database_sync_to_async
    def guardar_partida(self, numeros_ganadores, resultados):
        from .models import Partida, Apuesta, Jugador, Sala
        
        try:
            sala = Sala.objects.filter(activa=True).first()
            if not sala:
                return
            
            partida = Partida.objects.create(
                sala=sala,
                numeros_sorteados=numeros_ganadores,
                finalizada=True
            )
            
            for resultado in resultados:
                try:
                    jugador = Jugador.objects.get(nickname=resultado['nickname'])
                    
                    Apuesta.objects.create(
                        partida=partida,
                        jugador=jugador,
                        numeros_elegidos=resultado['numeros'],
                        aciertos=resultado['aciertos'],
                        puntos_ganados=resultado['puntos']
                    )
                    
                    jugador.puntos_totales += resultado['puntos']
                    jugador.partidas_jugadas += 1
                    jugador.save()

                except Jugador.DoesNotExist:
                    continue
                    
        except Exception as e:
            print(f"Error guardando partida: {e}")

import json
from channels.generic.websocket import AsyncWebsocketConsumer


class TableroConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_authenticated:
            self.group = f"user_{self.user.pk}"
            await self.channel_layer.group_add(self.group, self.channel_name)
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    # Nuevo traslado recibido
    async def nuevo_traslado(self, event):
        await self.send(text_data=json.dumps({
            "tipo": "traslado",
            "origen": event["origen"],
            "actividad": event["actividad"],
            "traslado_id": event["traslado_id"],
        }))

    # Nueva asignacion por planificacion
    async def nueva_asignacion(self, event):
        await self.send(text_data=json.dumps({
            "tipo": "asignacion",
            "actividad": event["actividad"],
            "fecha_programada": event.get("fecha_programada", ""),
        }))

    # Revision (aprobada o rechazada)
    async def actualizacion_revision(self, event):
        await self.send(text_data=json.dumps({
            "tipo": "revision",
            "accion": event["accion"],
            "actividad": event["actividad"],
            "comentario": event.get("comentario", ""),
        }))

    # Respuesta a traslado (aceptado/rechazado/cancelado)
    async def traslado_respuesta(self, event):
        await self.send(text_data=json.dumps({
            "tipo": "traslado_respuesta",
            "accion": event["accion"],
            "actividad": event["actividad"],
            "detalle": event.get("destino") or event.get("origen") or "",
        }))

    # Nueva historia en revision pendiente para el revisor
    async def nueva_revision(self, event):
        await self.send(text_data=json.dumps({
            "tipo": "nueva_revision",
            "historia": event["historia"],
            "codigo": event["codigo"],
            "proyecto": event["proyecto"],
        }))

    # Tarea rechazada (el Ejecutor es notificado)
    async def tarea_rechazada(self, event):
        await self.send(text_data=json.dumps({
            "tipo": "tarea_rechazada",
            "actividad": event["actividad"],
            "codigo": event["codigo"],
            "motivo": event["motivo"],
        }))

import json, uuid
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Conversation, Message

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id=self.scope["url_route"]["kwargs"]["conversation_id"]
        user=self.scope["user"]
        if not user.is_authenticated or not await self.allowed(user.id): await self.close(code=4403); return
        self.group=f"chat_{self.conversation_id}"; await self.channel_layer.group_add(self.group,self.channel_name); await self.accept()
    @database_sync_to_async
    def allowed(self,user_id): return Conversation.objects.filter(pk=self.conversation_id,participants__id=user_id).exists()
    @database_sync_to_async
    def save_message(self,body,client_id):
        m,_=Message.objects.get_or_create(sender=self.scope["user"],client_id=client_id,defaults={"conversation_id":self.conversation_id,"body":body})
        return {"id":str(m.id),"client_id":str(m.client_id),"body":m.body,"sender":m.sender.username,"created_at":m.created_at.isoformat()}
    async def receive(self,text_data):
        data=json.loads(text_data)
        if data.get("type")=="typing": await self.channel_layer.group_send(self.group,{"type":"chat.event","event":{"type":"typing","username":self.scope["user"].username}}); return
        event=await self.save_message(data.get("body","")[:4000],uuid.UUID(data.get("client_id",str(uuid.uuid4())))); await self.channel_layer.group_send(self.group,{"type":"chat.event","event":{"type":"message",**event}})
    async def chat_event(self,event): await self.send(text_data=json.dumps(event["event"]))
    async def disconnect(self,code):
        if hasattr(self,"group"): await self.channel_layer.group_discard(self.group,self.channel_name)

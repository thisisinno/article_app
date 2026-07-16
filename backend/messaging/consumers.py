import asyncio,json,uuid
from django.core import signing
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from accounts.models import User
from .models import Conversation,Message

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id=str(self.scope["url_route"]["kwargs"]["conversation_id"]);self.user=None;self.group=None
        origin=dict(self.scope.get("headers",[])).get(b"origin",b"").decode()
        if origin!="https://jesca.schoolsoft.online" and not (origin.startswith("https://") and origin.endswith(".app.github.dev")):await self.close(code=4403);return
        await self.accept();self.auth_timeout=asyncio.create_task(self.require_auth())
    async def require_auth(self):
        await asyncio.sleep(5)
        if self.user is None:await self.close(code=4401)
    @database_sync_to_async
    def authenticate_ticket(self,ticket):
        try:data=signing.loads(ticket,salt="insight.websocket",max_age=60)
        except signing.BadSignature:return None
        if str(data.get("conversation_id"))!=self.conversation_id:return None
        return User.objects.filter(pk=data.get("user_id"),conversations__pk=self.conversation_id,is_active=True).first()
    @database_sync_to_async
    def save_message(self,body,client_id):
        m,_=Message.objects.get_or_create(sender=self.user,client_id=client_id,defaults={"conversation_id":self.conversation_id,"body":body})
        return {"id":str(m.id),"client_id":str(m.client_id),"body":m.body,"sender":{"id":str(m.sender.public_id),"username":m.sender.username,"display_name":m.sender.display_name or m.sender.username,"avatar":None,"verified":False},"created_at":m.created_at.isoformat()}
    async def receive(self,text_data):
        try:data=json.loads(text_data)
        except json.JSONDecodeError:await self.close(code=4400);return
        if self.user is None:
            if data.get("type")!="authenticate":await self.close(code=4401);return
            self.user=await self.authenticate_ticket(data.get("ticket",""))
            if self.user is None:await self.close(code=4403);return
            self.auth_timeout.cancel();self.group=f"chat_{self.conversation_id}";await self.channel_layer.group_add(self.group,self.channel_name);await self.send(text_data=json.dumps({"type":"authenticated"}));return
        if data.get("type")=="typing":await self.channel_layer.group_send(self.group,{"type":"chat.event","event":{"type":"typing","username":self.user.username}});return
        try:client_id=uuid.UUID(data.get("client_id",str(uuid.uuid4())))
        except ValueError:await self.close(code=4400);return
        event=await self.save_message(data.get("body","")[:4000],client_id);await self.channel_layer.group_send(self.group,{"type":"chat.event","event":{"type":"message",**event}})
    async def chat_event(self,event):await self.send(text_data=json.dumps(event["event"]))
    async def disconnect(self,code):
        if getattr(self,"auth_timeout",None):self.auth_timeout.cancel()
        if self.group:await self.channel_layer.group_discard(self.group,self.channel_name)

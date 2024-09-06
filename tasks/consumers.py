import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import *
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .serializers import *

User = get_user_model()

class TaskConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.project_id = self.scope['url_route']['kwargs']['project_id']
        self.group_name = f"task_group_{self.project_id}"

        # Join room group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        user = self.scope['user'].username if self.scope['user'].is_authenticated else 'Anonymous'

        # Send message to room group
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'task_message',
                'message': message,
                'user': user,
            }
        )

    async def task_message(self, event):
        message = event['message']
        user = event['user']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'user': user,
        }))
        
    async def subtask_message(self, event):
        subtask = event['subtask']

        await self.send(text_data=json.dumps({
            'subtask': subtask,
        }))

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.project_id = self.scope['url_route']['kwargs']['project_id']
        self.group_name = f'chat_{self.project_id}'

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        user = self.scope['user']

        await self.save_message(user, message)

        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'chat_message',
                'message': message,
                'user': user.username,
            }
        )

    async def chat_message(self, event):
        message = event['message']
        user = event['user']

        await self.send(text_data=json.dumps({
            'user': user,
            'message': message,
        }))

    @database_sync_to_async
    def save_message(self, user, message):
        project = Project.objects.get(id=self.project_id)
        ChatMessage.objects.create(project=project, user=user, message=message)
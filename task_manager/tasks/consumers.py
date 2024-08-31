import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Task
from .serializers import TaskSerializer

class TaskConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = 'tasks'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        if 'task' in data:
            task_data = data['task']
            task = Task.objects.get(id=task_data['id'])
            serializer = TaskSerializer(task, data=task_data, partial=True)
            if serializer.is_valid():
                serializer.save()
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        'type': 'task_update',
                        'task': serializer.data
                    }
                )
            else:
                print(serializer.errors)

    async def task_update(self, event):
        task = event['task']
        await self.send(text_data=json.dumps({
            'type': 'update',
            'task': task
        }))

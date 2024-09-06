from rest_framework import serializers
from .models import *

from django.contrib.auth import get_user_model

User = get_user_model()

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'

class SubTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubTask
        fields = ['id', 'task', 'title', 'description', 'completed']

class ActivityLogSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.username')  # Serialize the username instead of ID

    class Meta:
        model = ActivityLog
        fields = ['user', 'action', 'task_title', 'from_status', 'to_status', 'edited_fields', 'timestamp']
        
class ChatMessageSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = ChatMessage
        fields = ['user', 'message', 'timestamp']
from django.db import models
from django.conf import settings

class Project(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        related_name='managed_projects', 
        on_delete=models.CASCADE,
        null=True,  # Allow null values
        blank=True  # Allow empty values in forms
    )
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='projects')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Task(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=50, choices=[('To-Do', 'To-Do'), ('Doing', 'Doing'), ('Done', 'Done')])
    owner = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='tasks', blank=True)  # Changed to ManyToManyField
    order = models.IntegerField(default=0)
    percentage = models.IntegerField(default=0)  
    deadline = models.DateTimeField(null=True, blank=True)  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    project = models.ForeignKey(Project, related_name='tasks', on_delete=models.CASCADE)

    class Meta:
        ordering = ['order']  # Default ordering by the order field
    
    def __str__(self):
        return self.title
    
class SubTask(models.Model):
    task = models.ForeignKey(Task, related_name='sub_tasks', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return self.title

class ActivityLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    action = models.CharField(max_length=255)
    task_title = models.CharField(max_length=255)
    from_status = models.CharField(max_length=255, null=True, blank=True)
    to_status = models.CharField(max_length=255, null=True, blank=True)
    edited_fields = models.CharField(max_length=255, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    project = models.ForeignKey(Project, related_name='activity_logs', on_delete=models.CASCADE) 

    def __str__(self):
        return f'{self.user.username if self.user else "Unknown User"} {self.action} "{self.task_title}" at {self.timestamp}'

class ChatMessage(models.Model):
    project = models.ForeignKey(Project, related_name='chat_messages', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username}: {self.message} ({self.timestamp})'
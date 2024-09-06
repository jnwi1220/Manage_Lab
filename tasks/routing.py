from django.urls import re_path
from .consumers import *

websocket_urlpatterns = [
    re_path(r'ws/projects/(?P<project_id>\d+)/tasks/$', TaskConsumer.as_asgi()),
    re_path(r'ws/chat/(?P<project_id>\d+)/$', ChatConsumer.as_asgi()),
    
]

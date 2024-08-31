from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'projects/(?P<project_id>\d+)/tasks', TaskViewSet, basename='project-tasks')
router.register(r'projects/(?P<project_id>\d+)/activity-logs', ActivityLogViewSet, basename='project-activity-logs')
router.register(r'projects/(?P<project_id>\d+)/chat-messages', ChatMessageViewSet, basename='project-chat-messages')
router.register(r'tasks/(?P<task_id>\d+)/sub-tasks', SubTaskViewSet, basename='sub-tasks')

urlpatterns = [
    path('', include(router.urls)),
    path('project_list/', project_list, name='project-list'),
    path('create_project/', create_project, name='create-project'),
    path('projects/<int:project_id>/', project_detail, name='project-detail'),
    path('projects/<int:project_id>/members/', project_members, name='project-members'),
    path('projects/<int:project_id>/invite/', invite_members_to_project, name='invite_members_to_project'),
    path('projects/<int:project_id>/set_manager/', set_project_manager, name='set-project-manager'), 
    path('projects/<int:project_id>/kickmember/<int:member_id>/', kick_member_from_project, name='kick-member'),

]

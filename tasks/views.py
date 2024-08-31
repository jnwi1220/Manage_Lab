from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework import viewsets, status
from .models import *
from .serializers import *
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import get_user_model

User = get_user_model()

####### START of View Set #######

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    def perform_create(self, serializer):
        serializer.save()

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    
    def get_queryset(self):
        project_id = self.kwargs.get('project_id')
        if project_id:
            return Task.objects.filter(project_id=project_id)
        return Task.objects.none()

    def perform_create(self, serializer):
        project_id = self.kwargs.get('project_id')
        project = get_object_or_404(Project, id=project_id)
        task = serializer.save(project=project)

        # Log the activity
        create_activity_log(
            user=self.request.user,
            project=project,
            action='created',
            task_title=task.title,
        )

        # Notify WebSocket clients
        notify_ws_clients(task, self.request.user, 'created')

    def perform_update(self, serializer):
        task = self.get_object()  # Get the existing task instance
        project = task.project

        # Store the original data
        original_data = {
            'title': task.title,
            'description': task.description,
            'owner': list(task.owner.values_list('username', flat=True)),  # Get the usernames of the original owners
            'status': task.status,
        }

        # Save the new data
        task = serializer.save()

        edited_fields = []

        # Track changes and log them
        for field in ['title', 'description']:
            old_value = original_data.get(field)
            new_value = serializer.validated_data.get(field)
            if old_value != new_value:
                edited_fields.append({
                    'field': field,
                    'from_value': old_value if old_value else 'None',
                    'to_value': new_value if new_value else 'None'
                })

        # Handle the owner field specifically
        new_owners = list(task.owner.values_list('username', flat=True))  # Get the new owner usernames
        if set(original_data['owner']) != set(new_owners):
            edited_fields.append({
                'field': 'owner',
                'from_value': ', '.join(original_data['owner']) if original_data['owner'] else 'None',
                'to_value': ', '.join(new_owners) if new_owners else 'None'
            })

        # Track status change separately since it affects the task's status
        original_status = original_data['status']
        new_status = serializer.validated_data.get('status', original_status)
        if original_status != new_status:
            create_activity_log(
                user=self.request.user,
                project=project,
                action='moved',
                task_title=task.title,
                from_status=original_status,
                to_status=new_status,
            )
            notify_ws_clients(task, self.request.user, 'moved', from_status=original_status, to_status=new_status)
        else:
            if edited_fields:
                create_activity_log(
                    user=self.request.user,
                    project=project,
                    action='edited',
                    task_title=task.title,
                    edited_fields=edited_fields,
                )
                notify_ws_clients(task, self.request.user, 'edited', edited_fields=edited_fields)

    def perform_destroy(self, instance):
        create_activity_log(
            user=self.request.user,
            project=instance.project,
            action='deleted',
            task_title=instance.title,
        )
        notify_ws_clients(instance, self.request.user, 'deleted')
        instance.delete()

    def destroy(self, request, *args, **kwargs):
        try:
            task = self.get_object()
            self.perform_destroy(task)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Task.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

class SubTaskViewSet(viewsets.ModelViewSet):
    serializer_class = SubTaskSerializer

    def get_queryset(self):
        task_id = self.kwargs.get('task_id')
        if task_id:
            return SubTask.objects.filter(task_id=task_id)
        return SubTask.objects.none()

    def perform_create(self, serializer):
        task = get_object_or_404(Task, id=self.kwargs.get('task_id'))
        sub_task = serializer.save(task=task)
        notify_ws_clients_subtask(sub_task, self.request.user, 'created')

    def perform_update(self, serializer):
        sub_task = serializer.save()
        notify_ws_clients_subtask(sub_task, self.request.user, 'updated')

    def perform_destroy(self, instance):
        notify_ws_clients_subtask(instance, self.request.user, 'deleted')
        instance.delete()

class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ActivityLogSerializer

    def get_queryset(self):
        project_id = self.kwargs.get('project_id')
        if project_id:
            return ActivityLog.objects.filter(project_id=project_id).order_by('-timestamp')
        return ActivityLog.objects.none()

class ChatMessageViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ChatMessageSerializer

    def get_queryset(self):
        project_id = self.kwargs['project_id']
        return ChatMessage.objects.filter(project_id=project_id).order_by('timestamp')

####### END of View Set #######


@csrf_exempt
@api_view(['POST'])
def create_project(request):
    # Get data from the request
    project_name = request.data.get('name')
    project_description = request.data.get('description')
    manager_id = request.data.get('manager_id')
    member_ids = request.data.get('members', [])

    # Validate the data
    if not project_name:
        return Response({"error": "Project name is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        manager = User.objects.get(id=manager_id) if manager_id else None
        project = Project.objects.create(
            name=project_name,
            description=project_description,
            manager=manager
        )
    
        # Add the manager as a member
        if manager:
            project.members.add(manager)

        # Add members to the project
        for member_id in member_ids:
            try:
                member = User.objects.get(id=member_id)
                project.members.add(member)
            except User.DoesNotExist:
                return Response({"error": f"User with ID {member_id} does not exist."}, status=status.HTTP_404_NOT_FOUND)


        return Response({'project': ProjectSerializer(project).data, "success": "Project created successfully!"}, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(['POST'])
def invite_members_to_project(request, project_id):
    try:
        # Get the project
        project = Project.objects.get(id=project_id)

        # Ensure the user making the request is either a project manager or member
        if request.user != project.manager and request.user not in project.members.all():
            return Response({"error": "You do not have permission to add members to this project."}, status=status.HTTP_403_FORBIDDEN)

        # Get the list of usernames from the request data
        usernames = request.data.get('usernames', [])

        for username in usernames:
            try:
                member = User.objects.get(username=username)
                project.members.add(member)
            except User.DoesNotExist:
                return Response({"error": f"User with username {username} does not exist."}, status=status.HTTP_404_NOT_FOUND)

        return Response({"success": "Members added successfully!"}, status=status.HTTP_200_OK)

    except Project.DoesNotExist:
        return Response({"error": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(['GET'])
def project_list(request):
    try:
        user = request.user
        print(f"User {user.username} is requesting projects.")
        projects = Project.objects.filter(members=user)
        serializer = ProjectSerializer(projects, many=True)
        print(f"Found {len(projects)} projects for user {user.username}.")
        return Response(serializer.data)
    except Exception as e:
        print(f"Error occurred: {e}")
        return Response({"error": str(e)}, status=500)
    
@api_view(['GET'])
def project_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    return JsonResponse({'name': project.name, 'manager': project.manager_id})

@api_view(['GET'])
def project_members(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    members = project.members.all()
    members_data = [{'username': member.username, 'email': member.email, 'id': member.id} for member in members]
    return JsonResponse(members_data, safe=False)

@api_view(['PATCH'])
def set_project_manager(request, project_id):
    try:
        project = get_object_or_404(Project, id=project_id)

        # Get the manager ID from the request data
        manager_id = request.data.get('manager_id')

        if not manager_id:
            return JsonResponse({'error': 'Manager ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Get the user to be set as manager
        manager = get_object_or_404(User, id=manager_id)

        # Update the project's manager
        project.manager = manager
        project.save()

        return JsonResponse({'success': f'{manager.username} has been set as the manager for this project.'})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
def kick_member_from_project(request, project_id, member_id):
    project = get_object_or_404(Project, id=project_id)
    member = get_object_or_404(User, id=member_id)

    # Ensure the user making the request is the project manager
    if request.user != project.manager:
        return Response({"error": "Only the project manager can kick members."}, status=status.HTTP_403_FORBIDDEN)

    if member == project.manager:
        return Response({"error": "You cannot kick the project manager."}, status=status.HTTP_400_BAD_REQUEST)

    # Remove the member from the project's members
    project.members.remove(member)

    return Response({"success": f"{member.username} has been removed from the project."}, status=status.HTTP_204_NO_CONTENT)

def create_activity_log(user, project, action, task_title, from_status=None, to_status=None, edited_fields=None):
    # Check if edited_fields are provided and are valid
    if edited_fields:
        formatted_edited_fields = []
        for field in edited_fields:
            # Check that both from_value and to_value are not None
            from_value = field.get('from_value', 'None')
            to_value = field.get('to_value', 'None')
            field_name = field.get('field', 'undefined')

            formatted_edited_fields.append(f"{field_name}: '{from_value}' to '{to_value}'")

        edited_fields_str = ', '.join(formatted_edited_fields) if formatted_edited_fields else None
    else:
        edited_fields_str = None

    ActivityLog.objects.create(
        user=user,
        project=project,
        action=action,
        task_title=task_title,
        from_status=from_status,
        to_status=to_status,
        edited_fields=edited_fields_str,
    )

def notify_ws_clients(task, user, action, from_status=None, to_status=None, edited_fields=None):
    channel_layer = get_channel_layer()

    message = {
        'user': user.username if user else 'Unknown User',
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'owner': task.owner,
        'status': task.status,
        'project_id': task.project.id,
        'action': action
    }
    
    if action == 'moved':
        message['from_status'] = from_status
        message['to_status'] = to_status
    if action == 'edited':
        message['edited_fields'] = edited_fields

    try:
        async_to_sync(channel_layer.group_send)(
            f"project_{task.project.id}",
            {
                'type': 'task_message',
                'message': message
            }
        )
    except Exception as e:
        # Log the error or handle it appropriately
        print(f"Failed to send WebSocket message: {e}")
        
        
def notify_ws_clients_subtask(sub_task, user, action):
    project_id = sub_task.task.project.id
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"task_group_{project_id}",
        {
            'type': 'subtask_message',
            'subtask': {
                'id': sub_task.id,
                'task_id': sub_task.task.id,
                'title': sub_task.title,
                'completed': sub_task.completed,
                'action': action,
                'user': user.username if user.is_authenticated else 'Anonymous'
            }
        }
    )
    



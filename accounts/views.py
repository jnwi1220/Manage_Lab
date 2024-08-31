from django.shortcuts import render, redirect
from rest_framework.response import Response
from django.contrib.auth import login, authenticate, get_user_model
from .forms import CustomUserCreationForm
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from rest_framework.decorators import api_view
from rest_framework import status
from django.db.models import Q

CustomUser = get_user_model()

@api_view(['GET'])
def current_user(request):
    user = request.user
    if user.is_authenticated:
        return Response({
            'id': user.id,
            'username': user.username,
        })
    else:
        return Response({'error': 'User is not authenticated'}, status=401)
    
@api_view(['GET'])
def get_user_by_username(request, username):
    try:
        user = CustomUser.objects.get(username=username)
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
        }, status=status.HTTP_200_OK)
    except CustomUser.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
def search_users(request):
    query = request.GET.get('q', '')
    users = CustomUser.objects.filter(Q(username__icontains=query))[:10]  # Limit to 10 results
    users_data = [{'username': user.username} for user in users]
    return JsonResponse(users_data, safe=False)
    
@csrf_exempt
def register_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            print(f"Received data: {data}")
            form = CustomUserCreationForm(data)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

        if form.is_valid():
            print("Form is valid!")
            user = form.save()
            login(request, user)
            return JsonResponse({'success': True}, status=200)
        else:
            errors = form.errors.get_json_data()
            print(f"Form errors: {errors}")
            return JsonResponse({'success': False, 'errors': errors}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        username = data.get('username')
        password = data.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return JsonResponse({'success': True}, status=200)
        else:
            return JsonResponse({'success': False, 'error': 'Invalid credentials'}, status=401)
    return JsonResponse({'error': 'Invalid request method'}, status=405)

from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('current_user/', views.current_user, name='current-user'),
    path('get_user_by_username/<str:username>/', views.get_user_by_username, name='get-user-by-username'),
    path('users/search/', views.search_users, name='user-search'),
]

release: python manage.py collectstatic --noinput
web: export DJANGO_SETTINGS_MODULE=task_manager.settings && daphne -p $PORT task_manager.asgi:application

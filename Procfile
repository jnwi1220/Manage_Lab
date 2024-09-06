release: python manage.py collectstatic --noinput
web: daphne -p 8000 -b 0.0.0.0 task_manager.asgi:application

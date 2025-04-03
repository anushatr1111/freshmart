import os
from django.core.wsgi import get_wsgi_application

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'grocery_store.settings')

# Get the WSGI application
application = get_wsgi_application()
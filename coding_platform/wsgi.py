import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coding_platform.settings')

application = get_wsgi_application()

# Alias for Vercel serverless functions
app = application

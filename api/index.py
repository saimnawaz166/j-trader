"""WSGI entrypoint Vercel's Python runtime serves the Django app through.

Not a Django app itself - just wires this project's WSGI application up
under Vercel's expected `app` variable name.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.wsgi import get_wsgi_application  # noqa: E402

app = get_wsgi_application()

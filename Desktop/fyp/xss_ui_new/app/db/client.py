"""Supabase client singleton. Import `db` anywhere in the app."""

from supabase import create_client, Client
from app.config import settings

db: Client = create_client(settings.supabase_url, settings.supabase_secret_key)

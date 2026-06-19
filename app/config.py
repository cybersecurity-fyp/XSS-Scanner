"""
app/config.py — Single source of truth for all settings.
Loads from .env in the project root. Fails fast if critical values are missing.
"""

import os
import sys
from dotenv import load_dotenv

# Load .env from the project root (two levels up from this file: app/ -> xss_ui_new/)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ROOT, '.env'), override=False, encoding='utf-8')


def _require(key: str) -> str:
    val = os.getenv(key, '')
    if not val or 'your_' in val or 'your-' in val:
        _fail(key)
    return val


def _fail(key: str) -> None:
    border = '=' * 60
    print(f'\n{border}')
    print('  XSSniper - Setup Required')
    print(f'  Missing or placeholder: {key}')
    print(f'  Edit .env and restart.')
    print(f'{border}\n')
    sys.exit(1)


def _require_session_secret() -> str:
    val = os.getenv('SESSION_SECRET', '')
    if not val or val == 'change_me_to_a_random_64_char_hex_string':
        print('\n  SESSION_SECRET not set. Generate one with:')
        print('  python -c "import secrets; print(secrets.token_hex(32))"')
        sys.exit(1)
    return val


class Settings:
    # Supabase
    supabase_url: str       = _require('SUPABASE_URL')
    supabase_secret_key: str = _require('SUPABASE_SECRET_KEY')
    supabase_publishable_key: str = os.getenv('SUPABASE_PUBLISHABLE_KEY', '')

    # Session
    session_secret: str = _require_session_secret()
    https_only: bool    = os.getenv('HTTPS_ONLY', 'false').lower() == 'true'

    # SMTP
    smtp_host: str  = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    smtp_port: int  = int(os.getenv('SMTP_PORT', '587'))
    smtp_user: str  = os.getenv('SMTP_USER', '')
    smtp_pass: str  = os.getenv('SMTP_PASS', '')
    smtp_from: str  = os.getenv('SMTP_FROM', '')

    # OAuth
    github_client_id: str     = os.getenv('GITHUB_CLIENT_ID', '')
    github_client_secret: str = os.getenv('GITHUB_CLIENT_SECRET', '')
    github_redirect_uri: str  = os.getenv('GITHUB_REDIRECT_URI', 'http://localhost:8080/auth/github/callback')

    google_client_id: str     = os.getenv('GOOGLE_CLIENT_ID', '')
    google_client_secret: str = os.getenv('GOOGLE_CLIENT_SECRET', '')
    google_redirect_uri: str  = os.getenv('GOOGLE_REDIRECT_URI', 'http://127.0.0.1:8080/auth/google/callback')

    # App
    app_base_url: str  = os.getenv('APP_BASE_URL', 'http://localhost:8080')
    expose_docs: bool  = os.getenv('EXPOSE_DOCS', 'false').lower() == 'true'

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_user and self.smtp_pass)

    @property
    def smtp_from_addr(self) -> str:
        return self.smtp_from or f'XSSniper <{self.smtp_user}>'


# Module-level singleton — import `settings` everywhere
settings = Settings()

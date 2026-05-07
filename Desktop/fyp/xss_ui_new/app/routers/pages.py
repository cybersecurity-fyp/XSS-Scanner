"""
app/routers/pages.py — All HTML page routes + health check + static file shortcuts.
These routes return rendered Jinja2 templates.
"""

import os
from datetime import datetime, timezone

import secrets as _secrets
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.dependencies import get_session_user
from app.db.scans import get_stats, get_history, get_daily_stats, init_db
from app.db.users import get_preferences
from app.services.auth_service import verify_email_token, verify_reset_token
from app.services.oauth_service import get_github_login_url, get_google_login_url

_TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'frontend', 'templates',
)
_STATIC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'frontend', 'static',
)

templates = Jinja2Templates(directory=_TEMPLATES_DIR)
router = APIRouter()


def _static(path: str) -> str:
    return os.path.join(_STATIC_DIR, path)


def _oauth_states(request: Request) -> tuple[str, str]:
    gh = _secrets.token_urlsafe(16)
    goog = _secrets.token_urlsafe(16)
    request.session['oauth_state_github'] = gh
    request.session['oauth_state_google'] = goog
    return gh, goog


# ── Health / Static shortcuts ─────────────────────────────────────────────────

@router.get('/health', include_in_schema=False)
async def health_check():
    from app.db.client import db
    ok = False
    try:
        db.table('users').select('id', count='exact').limit(1).execute()
        ok = True
    except Exception:
        pass
    return JSONResponse(
        {'status': 'ok' if ok else 'degraded',
         'db': 'connected' if ok else 'unreachable',
         'timestamp': datetime.utcnow().isoformat()},
        status_code=200 if ok else 503,
    )


@router.get('/robots.txt', include_in_schema=False)
async def robots():
    return FileResponse(_static('robots.txt'))


@router.get('/sw.js', include_in_schema=False)
async def sw():
    return FileResponse(
        _static('sw.js'),
        media_type='application/javascript',
        headers={'Service-Worker-Allowed': '/'}
    )


@router.get('/sitemap.xml', include_in_schema=False)
async def sitemap():
    return FileResponse(_static('sitemap.xml'), media_type='application/xml')


@router.get('/manifest.json', include_in_schema=False)
async def manifest():
    return FileResponse(_static('manifest.json'), media_type='application/manifest+json')


# ── Authenticated pages ───────────────────────────────────────────────────────

@router.get('/', response_class=HTMLResponse)
async def dashboard(request: Request):
    user = get_session_user(request)
    if not user:
        return RedirectResponse('/login')

    try:
        stats = get_stats(user_id=user['id'])
    except Exception:
        stats = {'total': 0, 'vulns': 0, 'health': 100.0}

    try:
        daily = get_daily_stats(user_id=user['id'])
    except Exception:
        daily = []

    try:
        history = get_history(user_id=user['id'])[:5]
    except Exception:
        history = []

    return templates.TemplateResponse(
        name="dashboard.html",
        request=request,
        context={
            "request": request,
            "user": user,
            "stats": stats,
            "daily": daily,
            "history": history,
            "active": "dashboard",
        }
    )


@router.get('/scan', response_class=HTMLResponse)
async def scan_page(request: Request):
    user = get_session_user(request)
    if not user:
        return RedirectResponse('/login')

    return templates.TemplateResponse(
        name="scan.html",
        request=request,
        context={
            "request": request,
            "user": user,
            "active": "scan",
        }
    )


@router.get('/history', response_class=HTMLResponse)
async def history_page(request: Request, page: int = 1):
    user = get_session_user(request)
    if not user:
        return RedirectResponse('/login')

    try:
        all_history = get_history(user_id=user['id'])
    except Exception:
        all_history = []

    per_page = 10
    total = len(all_history)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))

    return templates.TemplateResponse(
        name="history.html",
        request=request,
        context={
            "request": request,
            "user": user,
            "active": "history",
            "history": all_history[(page - 1) * per_page: page * per_page],
            "page": page,
            "total_pages": total_pages,
            "total": total,
        }
    )


@router.get('/settings', response_class=HTMLResponse)
async def settings_page(request: Request):
    user = get_session_user(request)
    if not user:
        return RedirectResponse('/login')

    db_info = {
        'host': settings.supabase_url.replace('https://', '').split('.supabase.co')[0] + '.supabase.co',
        'engine': 'PostgreSQL (Supabase)',
    }

    prefs = get_preferences(user['id'])

    return templates.TemplateResponse(
        name="settings.html",
        request=request,
        context={
            "request": request,
            "user": user,
            "active": "settings",
            "db_info": db_info,
            "prefs": prefs,
        }
    )


@router.get('/admin', response_class=HTMLResponse)
async def admin_page(request: Request):
    user = get_session_user(request)
    if not user:
        return RedirectResponse('/login')

    if user.get('role') != 'admin':
        return RedirectResponse('/')

    from app.db.users import get_all_users

    try:
        users = get_all_users()
    except Exception:
        users = []

    return templates.TemplateResponse(
        name="admin.html",
        request=request,
        context={
            "request": request,
            "user": user,
            "active": "admin",
            "users": users,
        }
    )


# ── Auth pages ───────────────────────────────────────────────────────────────

@router.get('/login', response_class=HTMLResponse)
async def login_page(request: Request):
    if get_session_user(request):
        return RedirectResponse('/')

    gh_state, goog_state = _oauth_states(request)

    return templates.TemplateResponse(
        name="login.html",
        request=request,
        context={
            "request": request,
            "github_url": get_github_login_url(gh_state),
            "google_url": get_google_login_url(goog_state),
        }
    )


@router.get('/register', response_class=HTMLResponse)
async def register_page(request: Request):
    if get_session_user(request):
        return RedirectResponse('/')

    gh_state, goog_state = _oauth_states(request)

    return templates.TemplateResponse(
        name="register.html",
        request=request,
        context={
            "request": request,
            "github_url": get_github_login_url(gh_state),
            "google_url": get_google_login_url(goog_state),
        }
    )


@router.get('/verify-email', response_class=HTMLResponse)
async def verify_email_page(request: Request, token: str = ''):
    if not token:
        return RedirectResponse('/login?error=invalid_token')

    success = verify_email_token(token)

    return templates.TemplateResponse(
        name="verify_email.html",
        request=request,
        context={
            "request": request,
            "success": success,
        }
    )


@router.get('/forgot-password', response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    if get_session_user(request):
        return RedirectResponse('/')

    return templates.TemplateResponse(
        name="forgot_password.html",
        request=request,
        context={"request": request}
    )


@router.get('/reset-password', response_class=HTMLResponse)
async def reset_password_page(request: Request, token: str = ''):
    if get_session_user(request):
        return RedirectResponse('/')

    if not token:
        return RedirectResponse('/forgot-password')

    user = verify_reset_token(token)

    if not user:
        return templates.TemplateResponse(
            name="reset_password.html",
            request=request,
            context={
                "request": request,
                "token": "",
                "error": "This reset link is invalid or has expired.",
            }
        )

    return templates.TemplateResponse(
        name="reset_password.html",
        request=request,
        context={
            "request": request,
            "token": token,
            "error": "",
            "username": user.get("username", ""),
        }
    )


@router.get('/terms', response_class=HTMLResponse)
async def terms_page(request: Request):
    return templates.TemplateResponse(
        name="terms.html",
        request=request,
        context={
            "request": request,
            "user": get_session_user(request),
        }
    )


@router.get('/privacy', response_class=HTMLResponse)
async def privacy_page(request: Request):
    return templates.TemplateResponse(
        name="privacy.html",
        request=request,
        context={
            "request": request,
            "user": get_session_user(request),
        }
    )
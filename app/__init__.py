"""
app/__init__.py — Application factory.
Call create_app() to get a configured FastAPI instance.
"""

import logging
import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.middleware import add_security_headers
from app.routers import pages, auth, scan, account, admin, export
from app.routers.auth import oauth_router

_HERE        = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_HERE)
_STATIC_DIR  = os.path.join(_PROJECT_DIR, 'frontend', 'static')
_TMPL_DIR    = os.path.join(_PROJECT_DIR, 'frontend', 'templates')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)


def create_app() -> FastAPI:
    app = FastAPI(
        title='XSSniper',
        docs_url='/docs'  if settings.expose_docs else None,
        redoc_url='/redoc' if settings.expose_docs else None,
    )

    # Rate limiting
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Session
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        https_only=settings.https_only,
        same_site='lax',
        session_cookie='xssniper_session',
        max_age=86400 * 30,
    )

    # Security headers
    app.middleware('http')(add_security_headers)

    # Static files
    app.mount('/static', StaticFiles(directory=_STATIC_DIR), name='static')

    # Routers — note: OAuth callbacks use /auth/... paths (not under /api/v1)
    app.include_router(pages.router)
    app.include_router(auth.router,    prefix='/api/v1/auth',    tags=['auth'])
    app.include_router(scan.router,    prefix='/api/v1/scan',    tags=['scan'])
    app.include_router(account.router, prefix='/api/v1/account', tags=['account'])
    app.include_router(admin.router,   prefix='/api/v1/admin',   tags=['admin'])
    app.include_router(export.router,  prefix='/api/v1',         tags=['data'])

    # OAuth callback routes — registered separately so only /auth/github/callback
    # and /auth/google/callback are exposed under /auth (not login/register/etc.)
    app.include_router(oauth_router,   prefix='/auth',            tags=['oauth'])

    _register_error_handlers(app)
    return app


def _register_error_handlers(app: FastAPI) -> None:
    tmpl = Jinja2Templates(directory=_TMPL_DIR)

    @app.exception_handler(404)
    async def not_found(request: Request, exc):
        user = request.session.get('user') if hasattr(request, 'session') else None
        return tmpl.TemplateResponse(request, '404.html', {'user': user}, status_code=404)

    @app.exception_handler(500)
    async def server_error(request: Request, exc):
        user = request.session.get('user') if hasattr(request, 'session') else None
        return tmpl.TemplateResponse(request, '500.html', {'user': user}, status_code=500)

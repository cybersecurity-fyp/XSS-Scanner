#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""XSSniper — entry point."""

import sys
import os

# Force UTF-8 console output on Windows
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app


def _print_startup_error(err: str) -> None:
    border = '=' * 60
    print(f'\n{border}')
    print('  XSSniper - Database Connection Failed')
    print(border)
    if 'getaddrinfo failed' in err or 'ConnectError' in err:
        print('  Cannot reach Supabase. Check SUPABASE_URL in .env')
    elif 'JWT' in err or '401' in err:
        print('  Invalid API key. Check SUPABASE_SECRET_KEY in .env')
    else:
        print(f'  Error: {err}')
    print(f'{border}\n')


# App instance (used by uvicorn/gunicorn when invoked as a module)
app = create_app()


if __name__ == '__main__':
    import uvicorn
    import logging

    log = logging.getLogger('xssniper')
    log.info('Starting XSSniper...')

    try:
        from app.db.scans import init_db
        init_db()
        log.info('Database OK - server starting on http://localhost:8080')
    except Exception as e:
        _print_startup_error(str(e))
        log.warning('Starting without database — some features will be unavailable.')

    uvicorn.run(app, host='0.0.0.0', port=8080, reload=False)

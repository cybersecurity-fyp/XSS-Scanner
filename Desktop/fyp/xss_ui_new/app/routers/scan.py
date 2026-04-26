"""app/routers/scan.py — Scan execution: start, stream logs (SSE), stop."""

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings
from app.dependencies import require_auth, validate_safe_url
from app.models.requests import ScanConfig
from app.services.scan_service import scan_service

log     = logging.getLogger('xssniper')
router  = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post('/start')
@limiter.limit('10/minute')
async def start_scan(config: ScanConfig, request: Request):
    user = require_auth(request)
    validate_safe_url(config.url)

    scan_id = uuid.uuid4().hex
    scan_service.create(scan_id, user['id'])

    async def _run():
        async def on_log(msg: str):
            pass  # logs stored in state; streamed via SSE

        result = await scan_service.run(scan_id, config.model_dump(), on_log=None)

        # Email notification on completion
        if settings.smtp_configured:
            try:
                from app.db.users import find_user_by_id
                from app.services.email_service import send_scan_complete_email
                db_user = find_user_by_id(user['id'])
                if db_user and db_user.get('email'):
                    send_scan_complete_email(
                        to_email=db_user['email'],
                        username=db_user.get('username', 'User'),
                        target_url=config.url,
                        vulnerabilities=result.get('vulnerabilities', 0),
                        duration=result.get('duration', 0),
                        status=result.get('status', 'completed'),
                    )
            except Exception as e:
                log.warning('Scan complete email failed: %s', e)

        # Auto-cleanup after 10 minutes
        await asyncio.sleep(600)
        scan_service.remove(scan_id)

    asyncio.create_task(_run())
    return {'scan_id': scan_id}


@router.get('/{scan_id}/stream')
async def stream_logs(scan_id: str, request: Request):
    user  = require_auth(request)
    state = scan_service.get(scan_id)

    if state and state.user_id and state.user_id != user['id']:
        raise HTTPException(403, 'Access denied')

    async def event_generator():
        last_idx = 0
        while True:
            state = scan_service.get(scan_id)
            if state is None:
                yield 'data: ERROR: Scan not found\n\n'
                break

            while last_idx < len(state.logs):
                yield f'data: {state.logs[last_idx]}\n\n'
                last_idx += 1

            if state.done:
                result = state.result or {}
                yield f'data: __DONE__{json.dumps(result)}\n\n'
                break

            await asyncio.sleep(0.1)

    return StreamingResponse(event_generator(), media_type='text/event-stream')


@router.post('/stop')
async def stop_scan(request: Request):
    user = require_auth(request)
    scan_id = scan_service.find_user_scan(user['id'])
    if scan_id:
        scan_service.stop(scan_id)
    return {'success': True}

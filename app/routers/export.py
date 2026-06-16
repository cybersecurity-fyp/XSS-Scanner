"""app/routers/export.py — Scan report exports: CSV, PDF, JSON."""

import logging
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.dependencies import require_auth
from app.db.scans import get_stats, get_history, get_scan_detail
from app.services import export_service

log    = logging.getLogger('xssniper')
router = APIRouter()


@router.get('/stats')
async def api_stats(request: Request):
    user = require_auth(request)
    return get_stats(user_id=user['id'])


@router.get('/history')
async def api_history(request: Request):
    user = require_auth(request)
    return get_history(user_id=user['id'])


@router.get('/history/{scan_id}')
async def api_scan_detail(scan_id: int, request: Request):
    user = require_auth(request)
    scan = get_scan_detail(scan_id)
    if not scan:
        raise HTTPException(404, 'Scan not found')
    _require_scan_owner(scan, user)
    return scan


@router.delete('/history/{scan_id}')
async def api_delete_scan(scan_id: int, request: Request):
    user = require_auth(request)
    from app.db.scans import delete_scan
    scan = get_scan_detail(scan_id)
    if not scan:
        raise HTTPException(404, 'Scan not found')
    _require_scan_owner(scan, user)
    if delete_scan(scan_id):
        return {'success': True}
    raise HTTPException(500, 'Delete failed')


@router.get('/csv/{scan_id}')
async def export_csv(scan_id: int, request: Request):
    user = require_auth(request)
    scan = _get_scan_or_404(scan_id)
    _require_scan_owner(scan, user)
    content = export_service.to_csv(scan)
    return Response(
        content=content,
        media_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename=scan_{scan_id}.csv'},
    )


@router.get('/json/{scan_id}')
async def export_json(scan_id: int, request: Request):
    user = require_auth(request)
    scan = _get_scan_or_404(scan_id)
    _require_scan_owner(scan, user)
    content = export_service.to_json(scan)
    return Response(
        content=content,
        media_type='application/json',
        headers={'Content-Disposition': f'attachment; filename=scan_{scan_id}.json'},
    )


@router.get('/pdf/{scan_id}')
async def export_pdf(scan_id: int, request: Request):
    user = require_auth(request)
    scan = _get_scan_or_404(scan_id)
    _require_scan_owner(scan, user)
    try:
        content = export_service.to_pdf(scan)
        return Response(
            content=content,
            media_type='application/pdf',
            headers={'Content-Disposition': f'attachment; filename=scan_{scan_id}.pdf'},
        )
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    except Exception as e:
        log.error('PDF generation failed for scan %s: %s', scan_id, e)
        raise HTTPException(500, 'PDF generation failed')


def _get_scan_or_404(scan_id: int) -> dict:
    scan = get_scan_detail(scan_id)
    if not scan:
        raise HTTPException(404, 'Scan not found')
    return scan


def _require_scan_owner(scan: dict, user: dict) -> None:
    """Raise 403 if the scan has a user_id that doesn't match the requesting user.
    Scans without a user_id (legacy data) are accessible to the owning user only
    when the user is an admin, otherwise allow access for backwards compatibility.
    """
    scan_uid = scan.get('user_id')
    if scan_uid is None:
        # Legacy scan with no owner recorded — allow if admin, otherwise allow
        # (this handles data created before user_id column was added)
        return
    if scan_uid != user['id'] and user.get('role') != 'admin':
        raise HTTPException(403, 'Access denied')

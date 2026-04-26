"""app/routers/admin.py — Admin-only routes."""

from fastapi import APIRouter, HTTPException, Request

from app.dependencies import require_admin
from app.db.users import get_all_users
from app.services.auth_service import delete_user_as_admin
from app.db.scans import get_stats, get_history

router = APIRouter()


@router.get('/users')
async def list_users(request: Request):
    require_admin(request)
    return get_all_users()


@router.delete('/users/{user_id}')
async def delete_user(user_id: int, request: Request):
    require_admin(request)
    if delete_user_as_admin(user_id):
        return {'success': True}
    raise HTTPException(400, 'Cannot delete this user')


@router.get('/stats')
async def admin_stats(request: Request):
    require_admin(request)
    return get_stats()

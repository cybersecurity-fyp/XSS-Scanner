"""app/routers/account.py — Account management: password, profile, preferences, delete."""

import logging
from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings
from app.dependencies import require_auth
from app.models.requests import ChangePasswordForm, UpdateProfileForm, DeleteAccountForm
from app.services import auth_service, email_service
from app.db.users import get_preferences, save_preferences

log     = logging.getLogger('xssniper')
router  = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post('/change-password')
@limiter.limit('10/minute')
async def change_password(form: ChangePasswordForm, request: Request):
    user = require_auth(request)

    if form.new_password != form.confirm_password:
        raise HTTPException(400, 'New passwords do not match')
    pw_ok, pw_err = auth_service.password_meets_requirements(form.new_password)
    if not pw_ok:
        raise HTTPException(400, pw_err)
    if not auth_service.verify_current_password(user['id'], form.current_password):
        raise HTTPException(400, 'Current password is incorrect')
    if form.new_password == form.current_password:
        raise HTTPException(400, 'New password must differ from the current one')
    if auth_service.update_password(user['id'], form.new_password):
        return {'success': True, 'message': 'Password changed successfully'}
    raise HTTPException(500, 'Failed to update password')


@router.post('/update-profile')
@limiter.limit('10/minute')
async def update_profile(form: UpdateProfileForm, request: Request):
    user = require_auth(request)

    if not auth_service.verify_current_password(user['id'], form.password):
        raise HTTPException(400, 'Incorrect password')

    if form.field == 'username':
        ok, err = auth_service.update_username(user['id'], form.value.strip())
        if not ok:
            raise HTTPException(400, err)
        request.session['user']['username'] = form.value.strip()
        return {'success': True, 'message': 'Username updated'}

    if form.field == 'email':
        ok, err = auth_service.update_email(user['id'], form.value.strip().lower())
        if not ok:
            raise HTTPException(400, err)
        if settings.smtp_configured:
            token = auth_service.create_verification_token(user['id'])
            email_service.send_verification_email(form.value.strip().lower(), user['username'], token)
        request.session['user']['email']          = form.value.strip().lower()
        request.session['user']['email_verified'] = False
        return {'success': True, 'message': 'Email updated. Please verify your new address.'}

    raise HTTPException(400, 'Invalid field')


@router.delete('/delete')
@limiter.limit('3/minute')
async def delete_account(form: DeleteAccountForm, request: Request):
    user = require_auth(request)

    if form.confirm_username != user['username']:
        raise HTTPException(400, 'Username confirmation does not match')

    ok, err = auth_service.delete_own_account(user['id'], form.password)
    if not ok:
        raise HTTPException(400, err)

    request.session.clear()
    log.info('Account deleted: %s', user.get('username'))
    return {'success': True}


@router.get('/preferences')
async def get_prefs(request: Request):
    user = require_auth(request)
    return get_preferences(user['id'])


@router.post('/preferences')
async def save_prefs(request: Request):
    user = require_auth(request)
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, 'Invalid preferences format')
    if save_preferences(user['id'], body):
        return {'success': True}
    raise HTTPException(500, 'Failed to save preferences')

"""app/db/scans.py — Scan table operations."""

import json
from datetime import datetime, timezone, timedelta, date
from typing import Optional
from app.db.client import db


def init_db() -> None:
    """Seed default admin user if users table is empty."""
    import hashlib, os
    resp = db.table('users').select('id', count='exact').execute()
    if (resp.count or 0) > 0:
        return
    # Simple one-time hash for the seed admin — use PBKDF2 from auth_service
    from app.services.auth_service import hash_password
    db.table('users').insert({
        'username': 'admin',
        'email':    'admin@xssniper.com',
        'password': hash_password('Admin@1234'),
        'role':     'admin',
        'email_verified': True,
    }).execute()


def save_scan(url: str, status: str, vulnerabilities: int,
              log_output: str, config: str, duration: float,
              user_id: Optional[int] = None) -> None:
    row = {
        'date':            datetime.now(timezone.utc).isoformat(),
        'url':             url,
        'status':          status,
        'vulnerabilities': vulnerabilities,
        'log_output':      log_output,
        'config':          config,
        'duration':        duration,
    }
    if user_id is not None:
        row['user_id'] = user_id
    db.table('scans').insert(row).execute()


def get_stats(user_id: Optional[int] = None) -> dict:
    q = db.table('scans').select('vulnerabilities, status, date')
    if user_id is not None:
        q = q.eq('user_id', user_id)
    resp = q.execute()
    rows = resp.data or []

    total = len(rows)
    vulns = sum(r.get('vulnerabilities', 0) or 0 for r in rows)
    vulnerable_scans = sum(1 for r in rows if (r.get('vulnerabilities', 0) or 0) > 0)
    clean_scans = total - vulnerable_scans

    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    recent = [r for r in rows if (r.get('date') or '') >= cutoff]
    if recent:
        clean_recent = sum(1 for r in recent if (r.get('vulnerabilities', 0) or 0) == 0)
        health = round(clean_recent * 100.0 / len(recent), 1)
    else:
        health = 100.0

    return {'total': total, 'vulns': vulns, 'health': health,
            'vulnerable_scans': vulnerable_scans, 'clean_scans': clean_scans}


def get_history(limit: int = 100, user_id: Optional[int] = None) -> list[dict]:
    q = db.table('scans').select('id, date, url, status, vulnerabilities, duration')
    if user_id is not None:
        q = q.eq('user_id', user_id)
    resp = q.order('date', desc=True).limit(limit).execute()
    return [_format_history_row(r) for r in (resp.data or [])]


def get_scan_detail(scan_id: int) -> Optional[dict]:
    try:
        resp = db.table('scans').select('*').eq('id', scan_id).single().execute()
    except Exception:
        return None
    r = resp.data
    if not r:
        return None
    return {
        'id':              r['id'],
        'user_id':         r.get('user_id'),
        'date':            r.get('date', ''),
        'url':             r.get('url', ''),
        'status':          r.get('status', ''),
        'vulnerabilities': r.get('vulnerabilities', 0),
        'log_output':      r.get('log_output', ''),
        'config':          json.loads(r['config']) if r.get('config') else {},
        'duration':        r.get('duration', 0),
    }


def get_daily_stats(days: int = 7, user_id: Optional[int] = None) -> list[dict]:
    """Return per-day scan counts and vulnerability totals for the last N days."""
    today  = date.today()
    result = []
    for offset in range(days - 1, -1, -1):
        day     = today - timedelta(days=offset)
        day_str = day.isoformat()          # '2026-03-19'
        label   = day.strftime('%b %d')    # 'Mar 19'
        q = db.table('scans').select('vulnerabilities').like('date', f'{day_str}%')
        if user_id is not None:
            q = q.eq('user_id', user_id)
        rows = (q.execute().data or [])
        result.append({
            'label': label,
            'scans': len(rows),
            'vulns': sum(r.get('vulnerabilities', 0) or 0 for r in rows),
        })
    return result


def delete_scan(scan_id: int) -> bool:
    try:
        db.table('scans').delete().eq('id', scan_id).execute()
        return True
    except Exception:
        return False


def _format_history_row(r: dict) -> dict:
    duration = r.get('duration')
    return {
        'id':              r['id'],
        'date':            (r.get('date') or '')[:19],
        'url':             r.get('url', ''),
        'status':          r.get('status', ''),
        'vulnerabilities': r.get('vulnerabilities', 0),
        'duration':        f'{duration:.2f}s' if duration else 'N/A',
    }

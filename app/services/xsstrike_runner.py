"""
app/services/xsstrike_runner.py — The ONLY module that knows about XSStrike.
Treats XSStrike as an external subprocess dependency.
Never import XSStrike internals; only call its CLI.
"""

import os
import re
import subprocess
import sys
from typing import Optional


def find_xsstrike() -> Optional[str]:
    """Find xsstrike.py — prefers Mariyam's ML-integrated xsstrike_code, falls back to XSStrike."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidates = [
        os.path.join(project_root, 'xsstrike_code', 'xsstrike.py'),  # Mariyam's ML version
        os.path.join(project_root, 'XSStrike', 'xsstrike.py'),
        os.path.join(project_root, 'xsstrike', 'xsstrike.py'),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def build_command(config: dict) -> list[str]:
    """
    Build the XSStrike CLI command from a scan config dict.
    All values are validated before being added to prevent command injection.
    """
    xsstrike_path = find_xsstrike()
    if not xsstrike_path:
        return []

    url = _validate_url(config.get('url', ''))
    if not url:
        raise ValueError('Invalid URL provided to XSStrike runner')

    cmd = [sys.executable, xsstrike_path, '-u', url, '--skip']

    if config.get('data'):
        cmd.extend(['--data', str(config['data'])[:4096]])  # length cap

    if config.get('json_mode'):
        cmd.append('--json')
    if config.get('crawl'):
        cmd.append('--crawl')
    if config.get('fuzzer'):
        cmd.append('--fuzzer')
    if config.get('encode'):
        cmd.append('--encode')
    if config.get('path'):
        cmd.append('--path')
    if config.get('skip_dom'):
        cmd.append('--skip-dom')

    level = _clamp_int(config.get('level', 2), 1, 3)
    if level != 2:
        cmd.extend(['-l', str(level)])

    threads = _clamp_int(config.get('threads', 2), 1, 10)
    if threads != 2:
        cmd.extend(['-t', str(threads)])

    timeout = _clamp_int(config.get('timeout', 5), 1, 60)
    if timeout != 5:
        cmd.extend(['--timeout', str(timeout)])

    delay = _clamp_float(config.get('delay', 0), 0, 30)
    if delay > 0:
        cmd.extend(['--delay', str(delay)])

    if config.get('headers'):
        cmd.extend(['--headers', str(config['headers'])[:2048]])

    if config.get('proxy'):
        proxy = _validate_proxy(config['proxy'])
        if proxy:
            cmd.extend(['--proxy', proxy])

    return cmd


def run_subprocess(cmd: list[str], payloads_file: Optional[str] = None) -> subprocess.Popen:
    """Start XSStrike subprocess and return the Popen handle.
    PYTHONPATH includes project root so xsstrike_ml imports resolve correctly.
    payloads_file sets XSSTRIKE_PAYLOADS_FILE so scan.py writes payloads there."""
    env = os.environ.copy()
    root = _project_root()
    existing = env.get('PYTHONPATH', '')
    env['PYTHONPATH'] = root + (os.pathsep + existing if existing else '')
    if payloads_file:
        env['XSSTRIKE_PAYLOADS_FILE'] = payloads_file
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
        env=env,
    )


def is_vulnerability_line(line: str) -> bool:
    """Check if a log line indicates a found vulnerability."""
    lower = line.lower()
    return any(kw in lower for kw in ('vulnerable', 'xss found', 'success'))


def is_ml_stats_line(line: str) -> bool:
    """Return True if line is part of the MLStats.report() block."""
    return any(kw in line for kw in (
        'ML INTEGRATION REPORT', 'Total payloads generated',
        'Payloads filtered by ML', 'Payloads sent to target',
        'Confirmed XSS payloads', '================================='
    ))


def extract_ml_stats(logs: list[str]) -> dict:
    """Parse MLStats.report() output from subprocess log lines."""
    stats = {}
    mapping = {
        'Total payloads generated': 'total_payloads',
        'Payloads filtered by ML': 'ml_filtered',
        'Payloads sent to target': 'sent_to_target',
        'Confirmed XSS payloads': 'confirmed_xss',
    }
    for line in logs:
        for label, key in mapping.items():
            if label in line:
                try:
                    stats[key] = int(line.split(':')[-1].strip())
                except ValueError:
                    pass
    return stats


# ── Input validation helpers ──────────────────────────────────────────────────

def _validate_url(url: str) -> Optional[str]:
    """Accept only http/https URLs with no shell-special characters."""
    url = url.strip()
    if not re.match(r'^https?://', url, re.IGNORECASE):
        return None
    if any(c in url for c in (';', '&&', '||', '`', '$', '\n', '\r')):
        return None
    return url


def _validate_proxy(proxy: str) -> Optional[str]:
    proxy = proxy.strip()
    if re.match(r'^https?://[a-zA-Z0-9._:\-]+$', proxy):
        return proxy
    return None


def _clamp_int(val, lo: int, hi: int) -> int:
    try:
        return max(lo, min(hi, int(val)))
    except (TypeError, ValueError):
        return lo


def _clamp_float(val, lo: float, hi: float) -> float:
    try:
        return max(lo, min(hi, float(val)))
    except (TypeError, ValueError):
        return lo

"""
app/services/scan_service.py — Scan lifecycle management.
Owns the active scan state. Calls xsstrike_runner (never touches XSStrike directly).
"""

import asyncio
import json
import logging
import os
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Callable, Optional, Awaitable

from app.db.scans import save_scan
from app.services import xsstrike_runner

log = logging.getLogger('xssniper')

AsyncLogCallback = Callable[[str], Awaitable[None]]

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _ensure_project_root_in_path() -> None:
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)


@dataclass
class ScanState:
    user_id: int
    logs:    list[str] = field(default_factory=list)
    done:    bool      = False
    stopped: bool      = False
    result:  Optional[dict] = None
    process: Optional[object] = None  # subprocess.Popen


class ScanService:
    """Manages the lifecycle of all active scans."""

    def __init__(self):
        self._active: dict[str, ScanState] = {}

    def create(self, scan_id: str, user_id: int) -> ScanState:
        state = ScanState(user_id=user_id)
        self._active[scan_id] = state
        return state

    def get(self, scan_id: str) -> Optional[ScanState]:
        return self._active.get(scan_id)

    def remove(self, scan_id: str) -> None:
        self._active.pop(scan_id, None)

    def find_user_scan(self, user_id: int) -> Optional[str]:
        """Return the scan_id of the active (not done) scan owned by user_id, or None."""
        for scan_id, state in self._active.items():
            if state.user_id == user_id and not state.done:
                return scan_id
        return None

    def stop(self, scan_id: str) -> None:
        state = self._active.get(scan_id)
        if not state:
            return
        state.stopped = True
        if state.process:
            try:
                state.process.terminate()
            except Exception:
                try:
                    state.process.kill()
                except Exception:
                    pass

    async def run(self, scan_id: str, config: dict,
                  on_log: Optional[AsyncLogCallback] = None) -> dict:
        """
        Execute a scan for scan_id. Calls back on_log for each output line.
        Saves result to DB when complete.
        """
        from datetime import datetime
        state = self._active.get(scan_id)
        if not state:
            return {'status': 'error', 'message': 'Scan not found'}

        started_at = datetime.now()

        # Per-scan temp file so concurrent scans don't collide
        payloads_fd, payloads_file = tempfile.mkstemp(
            prefix=f'xss_payloads_{scan_id}_', suffix='.txt'
        )
        os.close(payloads_fd)

        try:
            if config.get('ml_prefilter'):
                await self._emit_ml_prefilter(state, on_log)

            xsstrike_path = xsstrike_runner.find_xsstrike()

            if not xsstrike_path:
                await self._emit(state, on_log, '[WARN] XSStrike not found — running in simulation mode')
                await self._run_simulation(state, config['url'], on_log)
                vulnerabilities = 2
                ml_stats = {}
            else:
                vulnerabilities, ml_stats = await self._run_xsstrike(
                    state, config, on_log, payloads_file
                )

            if config.get('ml_prefilter'):
                await self._emit_ml_postfilter(state, on_log, payloads_file)

            variants = ml_stats.get('payload_variants', 0)
            if variants > 0:
                await self._emit(state, on_log,
                    f'[✓] 1 XSS reflection confirmed — {variants} exploit-capable payload variants detected')

            duration = (datetime.now() - started_at).total_seconds()
            save_scan(config['url'], 'Completed', vulnerabilities,
                      '\n'.join(state.logs), json.dumps(config), duration,
                      user_id=state.user_id)

            result = {
                'status': 'success',
                'vulnerabilities': vulnerabilities,
                'duration': duration,
                'ml_stats': ml_stats,
            }
            state.result = result
            return result

        except Exception as e:
            msg = f'[ERROR] Scan failed: {e}'
            await self._emit(state, on_log, msg)
            save_scan(config.get('url', 'unknown'), 'Failed', 0,
                      '\n'.join(state.logs), json.dumps(config), 0,
                      user_id=state.user_id)
            result = {'status': 'error', 'message': str(e)}
            state.result = result
            return result

        finally:
            state.done = True
            state.process = None
            try:
                os.unlink(payloads_file)
            except OSError:
                pass

    async def _run_xsstrike(self, state: ScanState, config: dict,
                             on_log: Optional[AsyncLogCallback],
                             payloads_file: str) -> tuple[int, dict]:
        cmd = xsstrike_runner.build_command(config)
        await self._emit(state, on_log, f'[*] Executing: {" ".join(cmd)}')

        env = os.environ.copy()
        root = xsstrike_runner._project_root()
        existing = env.get('PYTHONPATH', '')
        env['PYTHONPATH'] = root + (os.pathsep + existing if existing else '')
        env['XSSTRIKE_PAYLOADS_FILE'] = payloads_file

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
        )
        state.process = process
        payload_variants = 0   # ML-confirmed payloads ([CONFIRMED XSS] lines)
        xsstrike_vulns = 0     # XSStrike's own detections (crawl / non-ML path)

        while True:
            raw = await process.stdout.readline()
            if not raw:
                break
            if state.stopped:
                break
            line = raw.decode('utf-8', errors='replace').strip()
            if line:
                await self._emit(state, on_log, line)
                if '[CONFIRMED XSS]' in line:
                    payload_variants += 1
                elif xsstrike_runner.is_vulnerability_line(line):
                    xsstrike_vulns += 1

        await process.wait()
        ml_stats = xsstrike_runner.extract_ml_stats(state.logs)
        ml_stats['payload_variants'] = payload_variants

        # ML path: 1 reflection point per scan (N payload variants proved it)
        # Non-ML path (crawl etc.): use XSStrike's own detection count
        if payload_variants > 0:
            vulnerabilities = 1
        else:
            vulnerabilities = xsstrike_vulns
        return vulnerabilities, ml_stats

    async def _run_simulation(self, state: ScanState, url: str,
                               on_log: Optional[AsyncLogCallback]) -> None:
        lines = [
            f'[*] Target URL: {url}',
            '[*] Initializing XSStrike...',
            '[+] Loaded 247 XSS payloads',
            '[*] Analyzing parameters: [q, search, id]',
            '[*] Testing parameter: q',
            '[!] Potential XSS vector detected!',
            '[+] XSS VULNERABILITY FOUND!',
            '[+] Type: Reflected XSS | Parameter: q | Confidence: HIGH (94%)',
            '[*] Testing parameter: id',
            '[!] WAF detected, attempting bypass...',
            '[+] XSS VULNERABILITY FOUND!',
            '[+] Type: Reflected XSS | Parameter: id | Confidence: MEDIUM (78%)',
            '[*] Scan completed. Total vulnerabilities: 2',
        ]
        for line in lines:
            await self._emit(state, on_log, line)
            await asyncio.sleep(0.25)

    async def _emit_ml_prefilter(self, state: ScanState,
                                  on_log: Optional[AsyncLogCallback]) -> None:
        """Load the real ML prefilter model and report its status."""
        await self._emit(state, on_log, '[ML] Loading prefilter model...')
        try:
            _ensure_project_root_in_path()
            from xsstrike_ml.ml_prefilter import model, vectorizer, MODEL_TYPE
            if model is not None and vectorizer is not None:
                await self._emit(state, on_log,
                    f'[ML] Prefilter model loaded: {MODEL_TYPE.upper()} with TF-IDF vectorizer')
                await self._emit(state, on_log,
                    '[ML] Payloads will be scored before sending to target (threshold: 0.95)')
            else:
                await self._emit(state, on_log,
                    '[ML] Prefilter model unavailable — all payloads will be tested')
        except Exception as e:
            await self._emit(state, on_log, f'[ML] Prefilter load warning: {e}')

    async def _emit_ml_postfilter(self, state: ScanState,
                                   on_log: Optional[AsyncLogCallback],
                                   payloads_file: str) -> int:
        """Run the real ML postfilter model on payloads collected during the scan."""
        await self._emit(state, on_log, '[ML] Running ML postfilter on collected payloads...')

        payloads = []
        if os.path.exists(payloads_file):
            with open(payloads_file, 'r', encoding='utf-8') as f:
                payloads = [line.strip() for line in f if line.strip()]

        if not payloads:
            await self._emit(state, on_log, '[ML] No payloads collected for postfiltering')
            return 0

        await self._emit(state, on_log,
            f'[ML] Postfiltering {len(payloads)} collected payload(s) with trained model...')

        try:
            _ensure_project_root_in_path()
            from xsstrike_ml.postfilter import filter_payloads

            confirmed = filter_payloads(payloads, context='html_tag', threshold=0.9)

            await self._emit(state, on_log,
                f'[ML] Postfilter complete: {len(confirmed)}/{len(payloads)} payloads confirmed (confidence >= 0.90)')

            for i, payload in enumerate(confirmed[:5], 1):
                preview = payload[:80] + ('...' if len(payload) > 80 else '')
                await self._emit(state, on_log, f'[ML] Confirmed [{i}]: {preview}')

            return len(confirmed)

        except Exception as e:
            await self._emit(state, on_log, f'[ML] Postfilter error: {e}')
            return 0

    @staticmethod
    async def _emit(state: ScanState, on_log: Optional[AsyncLogCallback], msg: str) -> None:
        state.logs.append(msg)
        if on_log:
            await on_log(msg)


# Module singleton — one service instance for the app lifetime
scan_service = ScanService()

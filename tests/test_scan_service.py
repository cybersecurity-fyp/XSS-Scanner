"""
tests/test_scan_service.py — Unit tests for app/services/scan_service.py

ScanService manages in-memory scan state with no DB calls until run() completes.
These tests cover state management (create/get/stop/find) without hitting the DB.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ─────────────────────────────────────────────────────────────────────────────
#  ScanService state management  (no DB needed)
# ─────────────────────────────────────────────────────────────────────────────

class TestScanServiceState:
    def setup_method(self):
        from app.services.scan_service import ScanService
        self.service = ScanService()   # fresh instance per test

    def test_create_returns_scan_state(self):
        state = self.service.create('abc123', user_id=1)
        assert state is not None
        assert state.user_id == 1
        assert state.done is False
        assert state.stopped is False

    def test_get_returns_created_state(self):
        self.service.create('abc123', user_id=1)
        state = self.service.get('abc123')
        assert state is not None
        assert state.user_id == 1

    def test_get_unknown_scan_returns_none(self):
        assert self.service.get('nonexistent') is None

    def test_remove_clears_state(self):
        self.service.create('abc123', user_id=1)
        self.service.remove('abc123')
        assert self.service.get('abc123') is None

    def test_remove_nonexistent_is_noop(self):
        self.service.remove('never_existed')   # must not raise

    def test_find_user_scan_returns_active_scan_id(self):
        self.service.create('scan_A', user_id=5)
        result = self.service.find_user_scan(5)
        assert result == 'scan_A'

    def test_find_user_scan_returns_none_for_unknown_user(self):
        self.service.create('scan_A', user_id=5)
        assert self.service.find_user_scan(99) is None

    def test_find_user_scan_skips_done_scans(self):
        self.service.create('scan_A', user_id=5)
        self.service.get('scan_A').done = True
        assert self.service.find_user_scan(5) is None

    def test_find_user_scan_returns_only_own_scan(self):
        self.service.create('scan_A', user_id=1)
        self.service.create('scan_B', user_id=2)
        assert self.service.find_user_scan(1) == 'scan_A'
        assert self.service.find_user_scan(2) == 'scan_B'

    def test_stop_sets_stopped_flag(self):
        self.service.create('scan_A', user_id=1)
        self.service.stop('scan_A')
        assert self.service.get('scan_A').stopped is True

    def test_stop_terminates_process_if_present(self):
        self.service.create('scan_A', user_id=1)
        mock_proc = MagicMock()
        self.service.get('scan_A').process = mock_proc
        self.service.stop('scan_A')
        mock_proc.terminate.assert_called_once()

    def test_stop_nonexistent_scan_is_noop(self):
        self.service.stop('never_existed')  # must not raise


# ─────────────────────────────────────────────────────────────────────────────
#  ScanService.run() — simulation mode (XSStrike not found)
# ─────────────────────────────────────────────────────────────────────────────

class TestScanServiceRun:
    def setup_method(self):
        from app.services.scan_service import ScanService
        self.service = ScanService()

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_run_simulation_returns_success(self):
        self.service.create('sim1', user_id=7)
        config = {'url': 'https://example.com', 'ml_prefilter': False}

        with patch('app.services.scan_service.save_scan') as mock_save, \
             patch('app.services.xsstrike_runner.find_xsstrike', return_value=None):
            result = self._run(self.service.run('sim1', config))

        assert result['status'] == 'success'
        assert result['vulnerabilities'] == 2
        mock_save.assert_called_once()
        # Verify user_id was passed as keyword arg to save_scan
        call_kwargs = mock_save.call_args[1] if mock_save.call_args else {}
        assert call_kwargs.get('user_id') == 7

    def test_run_marks_state_done(self):
        self.service.create('sim2', user_id=7)
        config = {'url': 'https://example.com', 'ml_prefilter': False}

        with patch('app.services.xsstrike_runner.find_xsstrike', return_value=None), \
             patch('app.services.scan_service.save_scan'):
            self._run(self.service.run('sim2', config))

        state = self.service.get('sim2')
        assert state.done is True

    def test_run_unknown_scan_returns_error(self):
        config = {'url': 'https://example.com'}
        result = self._run(self.service.run('does_not_exist', config))
        assert result['status'] == 'error'

    def test_run_calls_on_log_callback(self):
        self.service.create('sim3', user_id=7)
        config = {'url': 'https://example.com', 'ml_prefilter': False}
        received = []

        async def collect(msg):
            received.append(msg)

        with patch('app.services.xsstrike_runner.find_xsstrike', return_value=None), \
             patch('app.services.scan_service.save_scan'):
            self._run(self.service.run('sim3', config, on_log=collect))

        assert len(received) > 0

    def test_run_with_ml_prefilter_emits_ml_lines(self):
        self.service.create('sim4', user_id=7)
        config = {'url': 'https://example.com', 'ml_prefilter': True}
        received = []

        async def collect(msg):
            received.append(msg)

        with patch('app.services.xsstrike_runner.find_xsstrike', return_value=None), \
             patch('app.services.scan_service.save_scan'):
            self._run(self.service.run('sim4', config, on_log=collect))

        ml_lines = [m for m in received if '[ML]' in m]
        assert len(ml_lines) > 0


# ─────────────────────────────────────────────────────────────────────────────
#  xsstrike_runner helpers  (pure functions, no DB or subprocess)
# ─────────────────────────────────────────────────────────────────────────────

class TestXSStrikeRunnerHelpers:
    def setup_method(self):
        from app.services import xsstrike_runner as r
        self.runner = r

    def test_validate_url_accepts_http(self):
        assert self.runner._validate_url('http://example.com') == 'http://example.com'

    def test_validate_url_accepts_https(self):
        assert self.runner._validate_url('https://example.com/page?q=1') is not None

    def test_validate_url_rejects_non_http(self):
        assert self.runner._validate_url('ftp://example.com') is None

    def test_validate_url_rejects_shell_chars(self):
        for evil in ['https://x.com;id', 'https://x.com&&ls', 'https://x.com`id`']:
            assert self.runner._validate_url(evil) is None, f'{evil!r} should be rejected'

    def test_clamp_int_within_range(self):
        assert self.runner._clamp_int(5, 1, 10) == 5

    def test_clamp_int_below_min(self):
        assert self.runner._clamp_int(0, 1, 10) == 1

    def test_clamp_int_above_max(self):
        assert self.runner._clamp_int(99, 1, 10) == 10

    def test_clamp_int_invalid_type_returns_lo(self):
        assert self.runner._clamp_int('bad', 1, 10) == 1

    def test_clamp_float_clamps_correctly(self):
        assert self.runner._clamp_float(35.0, 0, 30) == 30.0
        assert self.runner._clamp_float(-1.0, 0, 30) == 0.0

    def test_is_vulnerability_line_detects_keywords(self):
        assert self.runner.is_vulnerability_line('[+] XSS VULNERABLE found') is True
        assert self.runner.is_vulnerability_line('[+] xss found in param') is True
        assert self.runner.is_vulnerability_line('[*] Scanning parameters') is False

    def test_validate_proxy_accepts_valid(self):
        assert self.runner._validate_proxy('http://127.0.0.1:8080') == 'http://127.0.0.1:8080'

    def test_validate_proxy_rejects_shell_chars(self):
        assert self.runner._validate_proxy('http://x.com;rm -rf /') is None

    def test_build_command_raises_on_no_xsstrike(self):
        with patch.object(self.runner, 'find_xsstrike', return_value=None):
            result = self.runner.build_command({'url': 'https://example.com'})
        assert result == []

    def test_build_command_contains_url(self):
        with patch.object(self.runner, 'find_xsstrike', return_value='/fake/xsstrike.py'):
            cmd = self.runner.build_command({'url': 'https://example.com'})
        assert 'https://example.com' in cmd
        assert '-u' in cmd

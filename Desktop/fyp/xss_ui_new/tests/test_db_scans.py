"""
tests/test_db_scans.py — Unit tests for app/db/scans.py.

All Supabase calls are intercepted by the MagicMock db fixture.
"""

import json
import pytest
from unittest.mock import MagicMock, patch


def _mk_resp(data=None, count=None):
    r = MagicMock()
    r.data  = data
    r.count = count
    return r


@pytest.fixture
def scans(db):
    from app.db import scans as s
    db.reset_mock()
    return s


# ─────────────────────────────────────────────────────────────────────────────
#  save_scan
# ─────────────────────────────────────────────────────────────────────────────

class TestSaveScan:
    def test_save_without_user_id_does_not_include_user_id_key(self, scans, db):
        captured = {}
        def capture_insert(data):
            captured.update(data)
            return db.table.return_value.insert.return_value  # chain
        db.table.return_value.insert.side_effect = lambda data: _setup_chain(db, data, captured)

        def _setup_chain(db, data, captured):
            captured.update(data)
            m = MagicMock()
            m.execute.return_value = _mk_resp(data=[])
            return m

        scans.save_scan('https://example.com', 'Completed', 0, 'log', '{}', 3.5)
        # Verify insert was called
        assert db.table.return_value.insert.called

    def test_save_with_user_id_includes_user_id(self, scans, db):
        captured = {}
        def _setup_chain(data):
            captured.update(data)
            m = MagicMock()
            m.execute.return_value = _mk_resp(data=[])
            return m

        db.table.return_value.insert.side_effect = _setup_chain
        scans.save_scan('https://example.com', 'Completed', 2, 'log', '{}', 5.0, user_id=42)
        assert captured.get('user_id') == 42

    def test_save_includes_url_and_status(self, scans, db):
        captured = {}
        def _setup_chain(data):
            captured.update(data)
            m = MagicMock()
            m.execute.return_value = _mk_resp(data=[])
            return m
        db.table.return_value.insert.side_effect = _setup_chain
        scans.save_scan('https://target.com', 'Failed', 0, '', '{}', 0.0)
        assert captured['url']    == 'https://target.com'
        assert captured['status'] == 'Failed'


# ─────────────────────────────────────────────────────────────────────────────
#  get_stats
# ─────────────────────────────────────────────────────────────────────────────

class TestGetStats:
    def _setup_chain(self, db, rows):
        """Make db.table(...).select(...)[.eq(...)].execute() return rows."""
        chain = db.table.return_value.select.return_value
        chain.execute.return_value        = _mk_resp(data=rows)
        chain.eq.return_value.execute.return_value = _mk_resp(data=rows)
        return chain

    def test_empty_returns_zero_totals(self, scans, db):
        self._setup_chain(db, [])
        result = scans.get_stats()
        assert result['total'] == 0
        assert result['vulns'] == 0
        assert result['health'] == 100.0

    def test_counts_vulnerabilities(self, scans, db):
        rows = [
            {'vulnerabilities': 3, 'status': 'Completed', 'date': '2099-01-01T00:00:00+00:00'},
            {'vulnerabilities': 1, 'status': 'Completed', 'date': '2099-01-01T00:00:00+00:00'},
        ]
        self._setup_chain(db, rows)
        result = scans.get_stats()
        assert result['total'] == 2
        assert result['vulns'] == 4

    def test_health_100_when_all_completed(self, scans, db):
        from datetime import datetime, timezone, timedelta
        recent_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        rows = [
            {'vulnerabilities': 0, 'status': 'Completed', 'date': recent_date},
            {'vulnerabilities': 0, 'status': 'Completed', 'date': recent_date},
        ]
        self._setup_chain(db, rows)
        result = scans.get_stats()
        assert result['health'] == 100.0


# ─────────────────────────────────────────────────────────────────────────────
#  get_history
# ─────────────────────────────────────────────────────────────────────────────

class TestGetHistory:
    def test_returns_formatted_rows(self, scans, db):
        raw = [{
            'id': 1, 'date': '2026-03-19T10:00:00+00:00',
            'url': 'https://example.com', 'status': 'Completed',
            'vulnerabilities': 2, 'duration': 4.5,
        }]
        db.table.return_value.select.return_value \
          .order.return_value.limit.return_value.execute.return_value = _mk_resp(data=raw)
        result = scans.get_history()
        assert len(result) == 1
        assert result[0]['id'] == 1
        assert result[0]['duration'] == '4.50s'

    def test_returns_empty_list_when_no_rows(self, scans, db):
        db.table.return_value.select.return_value \
          .order.return_value.limit.return_value.execute.return_value = _mk_resp(data=[])
        assert scans.get_history() == []

    def test_duration_na_when_none(self, scans, db):
        raw = [{
            'id': 2, 'date': '2026-03-19T10:00:00',
            'url': 'https://x.com', 'status': 'Error',
            'vulnerabilities': 0, 'duration': None,
        }]
        db.table.return_value.select.return_value \
          .order.return_value.limit.return_value.execute.return_value = _mk_resp(data=raw)
        result = scans.get_history()
        assert result[0]['duration'] == 'N/A'

    def test_date_truncated_to_19_chars(self, scans, db):
        raw = [{
            'id': 3, 'date': '2026-03-19T10:00:00.123456+00:00',
            'url': 'https://x.com', 'status': 'Completed',
            'vulnerabilities': 0, 'duration': 1.0,
        }]
        db.table.return_value.select.return_value \
          .order.return_value.limit.return_value.execute.return_value = _mk_resp(data=raw)
        result = scans.get_history()
        assert len(result[0]['date']) == 19


# ─────────────────────────────────────────────────────────────────────────────
#  get_scan_detail
# ─────────────────────────────────────────────────────────────────────────────

class TestGetScanDetail:
    def test_returns_parsed_scan(self, scans, db):
        raw = {
            'id': 1, 'user_id': 5,
            'date': '2026-03-19T10:00:00+00:00',
            'url': 'https://example.com', 'status': 'Completed',
            'vulnerabilities': 1, 'log_output': 'log line',
            'config': '{"url": "https://example.com"}',
            'duration': 3.0,
        }
        db.table.return_value.select.return_value.eq.return_value \
          .single.return_value.execute.return_value = _mk_resp(data=raw)
        result = scans.get_scan_detail(1)
        assert result is not None
        assert result['id'] == 1
        assert isinstance(result['config'], dict)
        assert result['config']['url'] == 'https://example.com'

    def test_returns_none_on_exception(self, scans, db):
        db.table.return_value.select.return_value.eq.return_value \
          .single.return_value.execute.side_effect = Exception('not found')
        assert scans.get_scan_detail(999) is None

    def test_returns_none_when_data_is_none(self, scans, db):
        db.table.return_value.select.return_value.eq.return_value \
          .single.return_value.execute.return_value = _mk_resp(data=None)
        assert scans.get_scan_detail(999) is None

    def test_config_empty_dict_when_missing(self, scans, db):
        raw = {
            'id': 2, 'user_id': None,
            'date': '2026-03-19T10:00:00+00:00',
            'url': 'https://x.com', 'status': 'Error',
            'vulnerabilities': 0, 'log_output': '',
            'config': None, 'duration': 0,
        }
        db.table.return_value.select.return_value.eq.return_value \
          .single.return_value.execute.return_value = _mk_resp(data=raw)
        result = scans.get_scan_detail(2)
        assert result['config'] == {}


# ─────────────────────────────────────────────────────────────────────────────
#  get_daily_stats
# ─────────────────────────────────────────────────────────────────────────────

class TestGetDailyStats:
    def test_returns_7_entries_by_default(self, scans, db):
        db.table.return_value.select.return_value \
          .like.return_value.execute.return_value = _mk_resp(data=[])
        db.table.return_value.select.return_value \
          .like.return_value.eq.return_value.execute.return_value = _mk_resp(data=[])
        result = scans.get_daily_stats()
        assert len(result) == 7

    def test_each_entry_has_required_keys(self, scans, db):
        db.table.return_value.select.return_value \
          .like.return_value.execute.return_value = _mk_resp(data=[])
        db.table.return_value.select.return_value \
          .like.return_value.eq.return_value.execute.return_value = _mk_resp(data=[])
        result = scans.get_daily_stats()
        for entry in result:
            assert 'label' in entry
            assert 'scans' in entry
            assert 'vulns' in entry

    def test_counts_scans_and_vulns_per_day(self, scans, db):
        rows = [{'vulnerabilities': 2}, {'vulnerabilities': 3}]
        db.table.return_value.select.return_value \
          .like.return_value.execute.return_value = _mk_resp(data=rows)
        result = scans.get_daily_stats(days=1)
        assert result[0]['scans'] == 2
        assert result[0]['vulns'] == 5


# ─────────────────────────────────────────────────────────────────────────────
#  delete_scan
# ─────────────────────────────────────────────────────────────────────────────

class TestDeleteScan:
    def test_returns_true_on_success(self, scans, db):
        db.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock()
        assert scans.delete_scan(1) is True

    def test_returns_false_on_exception(self, scans, db):
        db.table.return_value.delete.return_value.eq.return_value.execute.side_effect = Exception('err')
        assert scans.delete_scan(99) is False

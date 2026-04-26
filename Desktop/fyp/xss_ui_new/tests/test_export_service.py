"""
tests/test_export_service.py — Unit tests for app/services/export_service.py.

to_csv, to_json, to_pdf are pure functions: they take a scan dict and return
bytes. No DB calls, no external dependencies (except optional reportlab for PDF).
"""

import csv
import io
import json
import pytest


SAMPLE_SCAN = {
    'id':              42,
    'date':            '2026-03-19T10:00:00+00:00',
    'url':             'https://example.com/search?q=test',
    'status':          'Completed',
    'vulnerabilities': 3,
    'log_output':      '[*] Scanning\n[+] XSS VULNERABLE found\n[+] XSS VULNERABLE found\n[+] XSS VULNERABLE found',
    'config':          {},
    'duration':        7.5,
}

SCAN_NO_LOG = {**SAMPLE_SCAN, 'log_output': '', 'vulnerabilities': 0}
SCAN_NONE_LOG = {**SAMPLE_SCAN, 'log_output': None}


@pytest.fixture
def service():
    from app.services import export_service
    return export_service


# ─────────────────────────────────────────────────────────────────────────────
#  to_csv
# ─────────────────────────────────────────────────────────────────────────────

class TestToCSV:
    def test_returns_bytes(self, service):
        result = service.to_csv(SAMPLE_SCAN)
        assert isinstance(result, bytes)

    def test_utf8_decodable(self, service):
        result = service.to_csv(SAMPLE_SCAN)
        decoded = result.decode('utf-8')
        assert len(decoded) > 0

    def test_has_header_row(self, service):
        result = service.to_csv(SAMPLE_SCAN).decode('utf-8')
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        assert rows[0] == ['Field', 'Value']

    def test_contains_scan_id(self, service):
        result = service.to_csv(SAMPLE_SCAN).decode('utf-8')
        assert '42' in result

    def test_contains_url(self, service):
        result = service.to_csv(SAMPLE_SCAN).decode('utf-8')
        assert 'https://example.com' in result

    def test_contains_vulnerabilities_count(self, service):
        result = service.to_csv(SAMPLE_SCAN).decode('utf-8')
        assert '3' in result

    def test_log_lines_present(self, service):
        result = service.to_csv(SAMPLE_SCAN).decode('utf-8')
        assert 'XSS VULNERABLE' in result

    def test_empty_log_does_not_crash(self, service):
        result = service.to_csv(SCAN_NO_LOG)
        assert isinstance(result, bytes)

    def test_none_log_does_not_crash(self, service):
        result = service.to_csv(SCAN_NONE_LOG)
        assert isinstance(result, bytes)

    def test_contains_status(self, service):
        result = service.to_csv(SAMPLE_SCAN).decode('utf-8')
        assert 'Completed' in result

    def test_contains_duration(self, service):
        result = service.to_csv(SAMPLE_SCAN).decode('utf-8')
        assert '7.5' in result


# ─────────────────────────────────────────────────────────────────────────────
#  to_json
# ─────────────────────────────────────────────────────────────────────────────

class TestToJSON:
    def test_returns_bytes(self, service):
        result = service.to_json(SAMPLE_SCAN)
        assert isinstance(result, bytes)

    def test_valid_json(self, service):
        result = service.to_json(SAMPLE_SCAN)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_has_scan_id_field(self, service):
        parsed = json.loads(service.to_json(SAMPLE_SCAN))
        assert parsed['scan_id'] == 42

    def test_has_url_field(self, service):
        parsed = json.loads(service.to_json(SAMPLE_SCAN))
        assert parsed['url'] == SAMPLE_SCAN['url']

    def test_has_status_field(self, service):
        parsed = json.loads(service.to_json(SAMPLE_SCAN))
        assert parsed['status'] == 'Completed'

    def test_has_vulnerabilities_field(self, service):
        parsed = json.loads(service.to_json(SAMPLE_SCAN))
        assert parsed['vulnerabilities'] == 3

    def test_has_duration_field(self, service):
        parsed = json.loads(service.to_json(SAMPLE_SCAN))
        assert parsed['duration'] == 7.5

    def test_has_log_output_field(self, service):
        parsed = json.loads(service.to_json(SAMPLE_SCAN))
        assert 'log_output' in parsed

    def test_all_expected_fields_present(self, service):
        parsed = json.loads(service.to_json(SAMPLE_SCAN))
        for field in ('scan_id', 'date', 'url', 'status', 'vulnerabilities', 'duration', 'log_output'):
            assert field in parsed, f'Missing field: {field}'

    def test_pretty_printed_has_indent(self, service):
        result = service.to_json(SAMPLE_SCAN).decode('utf-8')
        assert '\n' in result  # indent=2 produces newlines

    def test_unicode_url_handled(self, service):
        scan = {**SAMPLE_SCAN, 'url': 'https://例え.jp/search?q=テスト'}
        result = service.to_json(scan)
        parsed = json.loads(result)
        assert '例え.jp' in parsed['url']


# ─────────────────────────────────────────────────────────────────────────────
#  to_pdf
# ─────────────────────────────────────────────────────────────────────────────

class TestToPDF:
    def test_raises_runtime_error_if_reportlab_missing(self, service, monkeypatch):
        """Simulate reportlab not installed."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name.startswith('reportlab'):
                raise ImportError('No module named reportlab')
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, '__import__', mock_import)
        with pytest.raises(RuntimeError, match='reportlab'):
            service.to_pdf(SAMPLE_SCAN)

    def test_returns_bytes_when_reportlab_available(self, service):
        try:
            import reportlab  # noqa: F401
        except ImportError:
            pytest.skip('reportlab not installed')
        result = service.to_pdf(SAMPLE_SCAN)
        assert isinstance(result, bytes)

    def test_pdf_magic_bytes(self, service):
        try:
            import reportlab  # noqa: F401
        except ImportError:
            pytest.skip('reportlab not installed')
        result = service.to_pdf(SAMPLE_SCAN)
        assert result[:4] == b'%PDF'

    def test_pdf_with_zero_vulnerabilities(self, service):
        try:
            import reportlab  # noqa: F401
        except ImportError:
            pytest.skip('reportlab not installed')
        scan = {**SAMPLE_SCAN, 'vulnerabilities': 0}
        result = service.to_pdf(scan)
        assert result[:4] == b'%PDF'

    def test_pdf_with_none_log_output(self, service):
        try:
            import reportlab  # noqa: F401
        except ImportError:
            pytest.skip('reportlab not installed')
        result = service.to_pdf(SCAN_NONE_LOG)
        assert isinstance(result, bytes)

    def test_pdf_with_html_in_log_does_not_crash(self, service):
        """Log lines containing HTML entities must be escaped properly."""
        try:
            import reportlab  # noqa: F401
        except ImportError:
            pytest.skip('reportlab not installed')
        scan = {**SAMPLE_SCAN, 'log_output': '<script>alert(1)</script>'}
        result = service.to_pdf(scan)
        assert result[:4] == b'%PDF'

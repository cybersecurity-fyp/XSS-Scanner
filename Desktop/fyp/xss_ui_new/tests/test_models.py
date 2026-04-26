"""
tests/test_models.py — Unit tests for Pydantic request models in app/models/requests.py.

All models are tested for:
  - Valid inputs pass without errors
  - Field constraints (max_length, min_length, ge/le) reject invalid values
  - Custom validators (ScanConfig.url) work correctly
"""

import pytest
from pydantic import ValidationError


@pytest.fixture(scope='module')
def models():
    from app.models import requests
    return requests


# ─────────────────────────────────────────────────────────────────────────────
#  LoginForm
# ─────────────────────────────────────────────────────────────────────────────

class TestLoginForm:
    def test_valid_login(self, models):
        form = models.LoginForm(login='testuser', password='Pass@word1')
        assert form.login == 'testuser'

    def test_login_too_long_raises(self, models):
        with pytest.raises(ValidationError):
            models.LoginForm(login='x' * 300, password='Pass@word1')

    def test_password_too_long_raises(self, models):
        with pytest.raises(ValidationError):
            models.LoginForm(login='user', password='x' * 300)

    def test_missing_fields_raises(self, models):
        with pytest.raises(ValidationError):
            models.LoginForm()


# ─────────────────────────────────────────────────────────────────────────────
#  RegisterForm
# ─────────────────────────────────────────────────────────────────────────────

class TestRegisterForm:
    def test_valid_register(self, models):
        form = models.RegisterForm(
            username='testuser',
            email='test@example.com',
            password='Strong@Pass1',
            confirm='Strong@Pass1',
        )
        assert form.username == 'testuser'

    def test_email_too_long_raises(self, models):
        with pytest.raises(ValidationError):
            models.RegisterForm(
                username='user', email='x' * 300 + '@example.com',
                password='Pass@1', confirm='Pass@1',
            )

    def test_missing_confirm_raises(self, models):
        with pytest.raises(ValidationError):
            models.RegisterForm(username='user', email='a@b.com', password='Pass@1')


# ─────────────────────────────────────────────────────────────────────────────
#  ScanConfig — URL validation
# ─────────────────────────────────────────────────────────────────────────────

class TestScanConfigURL:
    def _make(self, models, url, **kwargs):
        defaults = dict(
            url=url, data='', level=2, threads=2, timeout=5, delay=0,
            json_mode=False, crawl=False, fuzzer=False, encode=False,
            path=False, skip_dom=False, ml_prefilter=False,
            headers='', proxy='', file='',
        )
        defaults.update(kwargs)
        return models.ScanConfig(**defaults)

    def test_valid_https_url_passes(self, models):
        cfg = self._make(models, 'https://example.com/search?q=1')
        assert cfg.url == 'https://example.com/search?q=1'

    def test_valid_http_url_passes(self, models):
        cfg = self._make(models, 'http://example.com')
        assert cfg.url.startswith('http://')

    def test_ftp_scheme_raises(self, models):
        with pytest.raises(ValidationError):
            self._make(models, 'ftp://example.com')

    def test_no_scheme_raises(self, models):
        with pytest.raises(ValidationError):
            self._make(models, 'example.com')

    def test_url_too_long_raises(self, models):
        with pytest.raises(ValidationError):
            self._make(models, 'https://example.com/' + 'a' * 3000)

    def test_url_whitespace_stripped(self, models):
        cfg = self._make(models, '  https://example.com  ')
        assert not cfg.url.startswith(' ')

    def test_url_max_length_boundary(self, models):
        url = 'https://example.com/' + 'a' * (2048 - 20)
        cfg = self._make(models, url)
        assert len(cfg.url) <= 2048


# ─────────────────────────────────────────────────────────────────────────────
#  ScanConfig — numeric field constraints
# ─────────────────────────────────────────────────────────────────────────────

class TestScanConfigNumericFields:
    BASE = dict(
        url='https://example.com', data='', json_mode=False,
        crawl=False, fuzzer=False, encode=False, path=False,
        skip_dom=False, ml_prefilter=False, headers='', proxy='', file='',
    )

    def test_level_valid_boundary_values(self, models):
        for level in (1, 2, 3):
            cfg = models.ScanConfig(**{**self.BASE, 'level': level})
            assert cfg.level == level

    def test_level_below_min_raises(self, models):
        with pytest.raises(ValidationError):
            models.ScanConfig(**{**self.BASE, 'level': 0})

    def test_level_above_max_raises(self, models):
        with pytest.raises(ValidationError):
            models.ScanConfig(**{**self.BASE, 'level': 4})

    def test_threads_valid_range(self, models):
        for t in (1, 5, 10):
            cfg = models.ScanConfig(**{**self.BASE, 'threads': t})
            assert cfg.threads == t

    def test_threads_below_min_raises(self, models):
        with pytest.raises(ValidationError):
            models.ScanConfig(**{**self.BASE, 'threads': 0})

    def test_threads_above_max_raises(self, models):
        with pytest.raises(ValidationError):
            models.ScanConfig(**{**self.BASE, 'threads': 11})

    def test_timeout_valid_range(self, models):
        for t in (1, 30, 60):
            cfg = models.ScanConfig(**{**self.BASE, 'timeout': t})
            assert cfg.timeout == t

    def test_timeout_below_min_raises(self, models):
        with pytest.raises(ValidationError):
            models.ScanConfig(**{**self.BASE, 'timeout': 0})

    def test_timeout_above_max_raises(self, models):
        with pytest.raises(ValidationError):
            models.ScanConfig(**{**self.BASE, 'timeout': 61})

    def test_delay_valid_range(self, models):
        for d in (0.0, 15.0, 30.0):
            cfg = models.ScanConfig(**{**self.BASE, 'delay': d})
            assert cfg.delay == d

    def test_delay_below_min_raises(self, models):
        with pytest.raises(ValidationError):
            models.ScanConfig(**{**self.BASE, 'delay': -1.0})

    def test_delay_above_max_raises(self, models):
        with pytest.raises(ValidationError):
            models.ScanConfig(**{**self.BASE, 'delay': 31.0})


# ─────────────────────────────────────────────────────────────────────────────
#  ScanConfig — optional string fields max_length
# ─────────────────────────────────────────────────────────────────────────────

class TestScanConfigStringFields:
    BASE = dict(
        url='https://example.com', level=2, threads=2, timeout=5, delay=0,
        json_mode=False, crawl=False, fuzzer=False, encode=False,
        path=False, skip_dom=False, ml_prefilter=False,
    )

    def test_data_too_long_raises(self, models):
        with pytest.raises(ValidationError):
            models.ScanConfig(**{**self.BASE, 'data': 'x' * 5000})

    def test_headers_too_long_raises(self, models):
        with pytest.raises(ValidationError):
            models.ScanConfig(**{**self.BASE, 'headers': 'X-Test: val\n' * 300})

    def test_proxy_too_long_raises(self, models):
        with pytest.raises(ValidationError):
            models.ScanConfig(**{**self.BASE, 'proxy': 'http://proxy.example.com/' + 'x' * 300})


# ─────────────────────────────────────────────────────────────────────────────
#  Other form models
# ─────────────────────────────────────────────────────────────────────────────

class TestOtherForms:
    def test_change_password_form_valid(self, models):
        form = models.ChangePasswordForm(
            current_password='OldPass@1',
            new_password='NewPass@1',
            confirm_password='NewPass@1',
        )
        assert form.current_password == 'OldPass@1'

    def test_delete_account_form_valid(self, models):
        form = models.DeleteAccountForm(
            password='Pass@word1',
            confirm_username='myuser',
        )
        assert form.confirm_username == 'myuser'

    def test_forgot_password_form_valid(self, models):
        form = models.ForgotPasswordForm(email='test@example.com')
        assert form.email == 'test@example.com'

    def test_forgot_password_email_too_long_raises(self, models):
        with pytest.raises(ValidationError):
            models.ForgotPasswordForm(email='x' * 300 + '@example.com')

    def test_reset_password_form_valid(self, models):
        form = models.ResetPasswordForm(
            token='tok123',
            password='NewPass@1',
            confirm='NewPass@1',
        )
        assert form.token == 'tok123'

    def test_update_profile_form_valid(self, models):
        form = models.UpdateProfileForm(
            field='username',
            value='newname',
            password='Pass@1',
        )
        assert form.field == 'username'

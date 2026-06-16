"""
app/services/email_service.py — SMTP email sending.
Returns (success, error_message) tuples so callers can handle failures.
"""

import smtplib
import ssl
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

log = logging.getLogger('xssniper')


def send_password_reset_email(to_email: str, username: str, token: str) -> tuple[bool, str]:
    reset_link = f'{settings.app_base_url}/reset-password?token={token}'
    subject    = 'XSSniper — Password Reset Request'
    text_body  = _reset_text(username, reset_link)
    html_body  = _reset_html(username, reset_link)
    return _send(to_email, subject, text_body, html_body)


def send_verification_email(to_email: str, username: str, token: str) -> tuple[bool, str]:
    link      = f'{settings.app_base_url}/verify-email?token={token}'
    subject   = 'XSSniper — Verify your email address'
    text_body = f'Hi {username},\n\nVerify your email:\n{link}\n\nLink expires in 24 hours.\n\n— XSSniper'
    html_body = _verification_html(username, link)
    return _send(to_email, subject, text_body, html_body)


def send_scan_complete_email(to_email: str, username: str, target_url: str,
                              vulnerabilities: int, duration: float, status: str) -> tuple[bool, str]:
    subject   = f'XSSniper — Scan {status.capitalize()}: {vulnerabilities} vulnerabilities found'
    text_body = (
        f'Hi {username},\n\nYour scan of {target_url} is complete.\n'
        f'Status: {status}\nVulnerabilities: {vulnerabilities}\nDuration: {duration:.2f}s\n\n— XSSniper'
    )
    html_body = _scan_complete_html(username, target_url, vulnerabilities, duration, status)
    return _send(to_email, subject, text_body, html_body)


# ── Core SMTP sender ──────────────────────────────────────────────────────────

def _send(to_email: str, subject: str, text_body: str, html_body: str) -> tuple[bool, str]:
    if not settings.smtp_configured:
        return False, 'SMTP not configured (set SMTP_USER and SMTP_PASS in .env)'

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = settings.smtp_from_addr
    msg['To']      = to_email
    msg.attach(MIMEText(text_body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(settings.smtp_user, settings.smtp_pass)
            server.sendmail(settings.smtp_from_addr, to_email, msg.as_string())
        return True, ''
    except smtplib.SMTPAuthenticationError:
        return False, 'SMTP authentication failed — check SMTP_USER and SMTP_PASS'
    except Exception as e:
        log.warning('Email send failed to %s: %s', to_email, e)
        return False, str(e)


# ── Email templates ───────────────────────────────────────────────────────────

_EMAIL_STYLE = '''
  body{margin:0;padding:0;background:#020408;font-family:'Segoe UI',Arial,sans-serif}
  .wrap{max-width:560px;margin:40px auto;background:#0a1520;border:1px solid #1a2e40;border-radius:16px;overflow:hidden}
  .header{background:linear-gradient(135deg,#0d1f2d,#0a2a1e);padding:32px 40px;text-align:center;border-bottom:1px solid #00ff8833}
  .logo{font-size:22px;font-weight:800;color:#00ff88;letter-spacing:4px;font-family:'Courier New',monospace}
  .body{padding:32px 40px}
  .btn{display:inline-block;background:#00ff88;color:#040e08;font-weight:700;padding:14px 32px;border-radius:8px;text-decoration:none;font-size:15px;letter-spacing:1px}
  .footer{padding:20px 40px;border-top:1px solid #1a2e40;font-size:12px;color:#4a6a7a;text-align:center}
  p{color:#8892a4;line-height:1.6}
'''


def _reset_text(username: str, link: str) -> str:
    return (
        f'Hi {username},\n\nYou requested a password reset for your XSSniper account.\n\n'
        f'Reset link (valid for 1 hour):\n{link}\n\n'
        f'If you did not request this, ignore this email.\n\n— XSSniper'
    )


def _reset_html(username: str, link: str) -> str:
    return f'''<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>{_EMAIL_STYLE}</style></head>
<body><div class="wrap">
  <div class="header"><div style="font-size:28px;margin-bottom:6px">🛡️</div><div class="logo">XSSNIPER</div></div>
  <div class="body">
    <h2 style="color:#00ff88;margin-top:0">Password Reset</h2>
    <p>Hi <strong style="color:#c8d0dc">{username}</strong>,</p>
    <p>Click the button below to reset your password. This link is valid for <strong>1 hour</strong>.</p>
    <p style="text-align:center;margin:28px 0"><a href="{link}" class="btn">RESET PASSWORD</a></p>
    <p>If you did not request a password reset, ignore this email.</p>
  </div>
  <div class="footer">© XSSniper Security Tool</div>
</div></body></html>'''


def _verification_html(username: str, link: str) -> str:
    return f'''<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>{_EMAIL_STYLE}</style></head>
<body><div class="wrap">
  <div class="header"><div style="font-size:28px;margin-bottom:6px">🛡️</div><div class="logo">XSSNIPER</div></div>
  <div class="body">
    <h2 style="color:#00ff88;margin-top:0">Verify Your Email</h2>
    <p>Hi <strong style="color:#c8d0dc">{username}</strong>,</p>
    <p>Click below to verify your email address. The link expires in <strong>24 hours</strong>.</p>
    <p style="text-align:center;margin:28px 0"><a href="{link}" class="btn">VERIFY EMAIL</a></p>
  </div>
  <div class="footer">© XSSniper Security Tool</div>
</div></body></html>'''


def _scan_complete_html(username: str, url: str, vulns: int, duration: float, status: str) -> str:
    color  = '#ff3b5c' if vulns > 0 else '#00ff88'
    return f'''<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>{_EMAIL_STYLE}</style></head>
<body><div class="wrap">
  <div class="header"><div style="font-size:28px;margin-bottom:6px">🛡️</div><div class="logo">XSSNIPER</div></div>
  <div class="body">
    <h2 style="color:#00ff88;margin-top:0">Scan Complete</h2>
    <p>Hi <strong style="color:#c8d0dc">{username}</strong>,</p>
    <p>Your scan of <code style="color:#00d9ff">{url}</code> has finished.</p>
    <table style="width:100%;border-collapse:collapse;margin:16px 0">
      <tr><td style="padding:8px;color:#8892a4">Status</td><td style="padding:8px;color:#c8d0dc">{status.capitalize()}</td></tr>
      <tr style="background:#0f1621"><td style="padding:8px;color:#8892a4">Vulnerabilities</td><td style="padding:8px;color:{color};font-weight:700">{vulns}</td></tr>
      <tr><td style="padding:8px;color:#8892a4">Duration</td><td style="padding:8px;color:#c8d0dc">{duration:.2f}s</td></tr>
    </table>
  </div>
  <div class="footer">© XSSniper Security Tool</div>
</div></body></html>'''

"""All Pydantic request schemas in one place."""

import re
from pydantic import BaseModel, Field, field_validator


class LoginForm(BaseModel):
    login:    str = Field(..., max_length=254)
    password: str = Field(..., max_length=256)


class RegisterForm(BaseModel):
    username: str = Field(..., min_length=3,  max_length=32)
    email:    str = Field(..., max_length=254)
    password: str = Field(..., max_length=256)
    confirm:  str = Field(..., max_length=256)


class ForgotPasswordForm(BaseModel):
    email: str = Field(..., max_length=254)


class ResetPasswordForm(BaseModel):
    token:    str = Field(..., max_length=128)
    password: str = Field(..., max_length=256)
    confirm:  str = Field(..., max_length=256)


class ChangePasswordForm(BaseModel):
    current_password: str = Field(..., max_length=256)
    new_password:     str = Field(..., max_length=256)
    confirm_password: str = Field(..., max_length=256)


class UpdateProfileForm(BaseModel):
    field:    str = Field(..., max_length=16)   # 'username' or 'email'
    value:    str = Field(..., max_length=254)
    password: str = Field(..., max_length=256)  # requires password confirmation


class DeleteAccountForm(BaseModel):
    password:         str = Field(..., max_length=256)
    confirm_username: str = Field(..., max_length=32)


class ResendVerifyForm(BaseModel):
    email: str = Field(..., max_length=254)


class ScanConfig(BaseModel):
    url:          str   = Field(..., max_length=2048)
    data:         str   = Field('', max_length=4096)
    json_mode:    bool  = False
    crawl:        bool  = False
    level:        int   = Field(2, ge=1, le=3)
    threads:      int   = Field(2, ge=1, le=10)
    timeout:      int   = Field(5, ge=1, le=60)
    delay:        float = Field(0, ge=0, le=30)
    fuzzer:       bool  = False
    encode:       bool  = False
    path:         bool  = False
    file:         str   = Field('', max_length=512)
    skip_dom:     bool  = False
    headers:      str   = Field('', max_length=2048)
    proxy:        str   = Field('', max_length=256)
    ml_prefilter: bool  = False

    @field_validator('url')
    @classmethod
    def url_must_be_http(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r'^https?://', v, re.IGNORECASE):
            raise ValueError('URL must start with http:// or https://')
        return v

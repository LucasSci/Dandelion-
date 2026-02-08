import json
import os
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from utils.audit import log_audit_event
from utils.crypto import decrypt_sensitive_data, encrypt_sensitive_data
from utils.security import SecurityContext, authorize_action, generate_totp, verify_totp


def test_rbac_and_abac_allows_owner():
    context = SecurityContext(
        user_id="user-1",
        roles=("player",),
        org_id="org-1",
        attributes={},
        mfa_verified=False,
    )
    assert authorize_action(
        context,
        "vtt:roll",
        {"org_id": "org-1", "owner_id": "user-1"},
    )


def test_abac_denies_cross_org():
    context = SecurityContext(
        user_id="user-2",
        roles=("player",),
        org_id="org-1",
        attributes={},
        mfa_verified=False,
    )
    assert not authorize_action(
        context,
        "vtt:roll",
        {"org_id": "org-2"},
    )


def test_totp_verification():
    secret = "JBSWY3DPEHPK3PXP"
    now = 1_700_000_000
    token = generate_totp(secret, for_time=now)
    assert verify_totp(secret, token, for_time=now)


def test_encrypt_decrypt_sensitive_data(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", key)
    plaintext = "sensitive"
    encrypted = encrypt_sensitive_data(plaintext)
    assert encrypted != plaintext
    decrypted = decrypt_sensitive_data(encrypted)
    assert decrypted == plaintext


def test_audit_log_encrypted_fields(tmp_path, monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", key)
    log_path = tmp_path / "audit.log"
    monkeypatch.setenv("AUDIT_LOG_PATH", str(log_path))
    log_audit_event({"event": "login", "user_id": "user-1"}, encrypt_fields={"user_id"})

    assert log_path.exists()
    payload = json.loads(Path(log_path).read_text(encoding="utf-8").strip())
    assert payload["event"] == "login"
    assert payload["user_id"] != "user-1"

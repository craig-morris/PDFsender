#!/usr/bin/env python3
"""Shared SMTP authentication helpers for PDFsender."""

from __future__ import annotations

from typing import Tuple


def build_smtp_auth_payload(username: str, password: str, auth_type: str, access_token: str) -> Tuple[str, str, str]:
    auth_type = (auth_type or "login").strip().lower()
    if auth_type == "xoauth2":
        if not access_token:
            raise ValueError("Access token is required for XOAUTH2 auth")
        return auth_type, username, access_token
    if auth_type == "login":
        return auth_type, username, password
    raise ValueError(f"Unsupported SMTP auth type: {auth_type}")

#!/usr/bin/env python3
"""Quick SMTP credential test for PDFsender."""

from __future__ import annotations

import argparse
import os
import smtplib
import ssl
import sys
from pathlib import Path

from pdf_auto_sender import load_config_file
from smtp_utils import build_smtp_auth_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test SMTP credentials")
    parser.add_argument("--smtp-host", default="", help="SMTP host")
    parser.add_argument("--smtp-port", default="587", help="SMTP port")
    parser.add_argument("--smtp-user", default="", help="SMTP username")
    parser.add_argument("--smtp-password", default="", help="SMTP password")
    parser.add_argument("--smtp-auth-type", default=os.getenv("SMTP_AUTH_TYPE", "login"), help="SMTP auth type: login or xoauth2")
    parser.add_argument("--smtp-access-token", default=os.getenv("SMTP_ACCESS_TOKEN", ""), help="OAuth access token")
    parser.add_argument("--config", default=".env", help="Path to a .env-style config file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_dir = Path(__file__).resolve().parent
    config_path = (base_dir / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config)
    config_values = load_config_file(config_path)

    args.smtp_host = args.smtp_host or os.getenv("SMTP_HOST") or config_values.get("SMTP_HOST", "")
    args.smtp_port = args.smtp_port or os.getenv("SMTP_PORT") or config_values.get("SMTP_PORT", "587")
    args.smtp_user = args.smtp_user or os.getenv("SMTP_USER") or config_values.get("SMTP_USER", "")
    args.smtp_password = args.smtp_password or os.getenv("SMTP_PASSWORD") or config_values.get("SMTP_PASSWORD", "")
    args.smtp_auth_type = args.smtp_auth_type or os.getenv("SMTP_AUTH_TYPE") or config_values.get("SMTP_AUTH_TYPE", "login")
    args.smtp_access_token = args.smtp_access_token or os.getenv("SMTP_ACCESS_TOKEN") or config_values.get("SMTP_ACCESS_TOKEN", "")

    if not args.smtp_host or not args.smtp_user or (not args.smtp_password and args.smtp_auth_type != "xoauth2"):
        print("SMTP host, username, and password are required. For XOAUTH2, provide an access token.")
        return 2

    port = int(args.smtp_port)
    try:
        if port == 465:
            server = smtplib.SMTP_SSL(args.smtp_host, port, timeout=20)
        else:
            server = smtplib.SMTP(args.smtp_host, port, timeout=20)
            server.starttls(context=ssl.create_default_context())

        server.ehlo()
        auth_type, auth_user, auth_secret = build_smtp_auth_payload(
            args.smtp_user,
            args.smtp_password,
            args.smtp_auth_type,
            args.smtp_access_token,
        )
        if auth_type == "xoauth2":
            server.auth("XOAUTH2", lambda _: auth_secret.encode("utf-8"))
        else:
            server.login(auth_user, auth_secret)
        print("SMTP authentication successful")
        server.quit()
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"SMTP authentication failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

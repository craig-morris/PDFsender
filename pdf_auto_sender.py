#!/usr/bin/env python3
"""
PDFsender 2.0
Author: Script Kid
Version: 2.0

Lightweight SMTP sender for plain-text email bodies with PDF attachments.
Supports SMTP rotation across multiple hosts and ports 587/465.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import re
import smtplib
import ssl
import sys
import time
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Dict, List, Tuple

from smtp_utils import build_smtp_auth_payload

APP_NAME = "PDFsender"
VERSION = "2.0"


def load_config_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--leads", default="list.txt", help="Path to the leads file")
    parser.add_argument("--body-template", default="body_template.md", help="Markdown body template")
    parser.add_argument("--pdf", default="sample.pdf", help="PDF file to attach, or a directory of PDFs to rotate")
    parser.add_argument("--subject", default="Secure Document Portal", help="Email subject")
    parser.add_argument("--smtp-host", default="", help="SMTP host or comma-separated hosts")
    parser.add_argument("--smtp-port", default="587", help="SMTP port or comma-separated ports")
    parser.add_argument("--smtp-user", default="", help="SMTP username")
    parser.add_argument("--smtp-password", default="", help="SMTP password")
    parser.add_argument("--from-email", default="", help="Sender email address")
    parser.add_argument("--sender-name", default="Microsoft Azure CLI", help="Sender display name")
    parser.add_argument("--mail-client", default="Microsoft Azure CLI", help="Value for the X-Mailer header")
    parser.add_argument("--sender-host", default="Microsoft Azure CLI", help="Host label included in authentication headers")
    parser.add_argument("--authentication-results", default="dkim=pass spf=pass dmarc=pass", help="Authentication-Results header value")
    parser.add_argument("--throttle-seconds", type=float, default=0, help="Delay in seconds between sends")
    parser.add_argument("--out-dir", default="out", help="Directory for sent/failed/log files")
    parser.add_argument("--dry-run", action="store_true", help="Parse leads and render emails without sending")
    parser.add_argument("--config", default=".env", help="Path to a .env-style config file")
    parser.add_argument("--smtp-auth-type", default=os.getenv("SMTP_AUTH_TYPE", "login"), help="SMTP auth mode: login or xoauth2")
    parser.add_argument("--smtp-access-token", default=os.getenv("SMTP_ACCESS_TOKEN", ""), help="Access token for XOAUTH2 auth")
    return parser.parse_args()


def setup_logging(out_dir: Path) -> logging.Logger:
    out_dir.mkdir(parents=True, exist_ok=True)
    log_file = out_dir / "logs" / "smtp_sender.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("pdf_auto_sender")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger


def ensure_outputs(out_dir: Path) -> Tuple[Path, Path, Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "logs").mkdir(parents=True, exist_ok=True)
    sent_file = out_dir / "sent.txt"
    delivered_file = out_dir / "delivered.txt"
    failed_file = out_dir / "failed.txt"
    campaign_log = out_dir / "campaign_sent_output.log"

    for path in [sent_file, delivered_file, failed_file, campaign_log]:
        if not path.exists():
            path.write_text("", encoding="utf-8")

    return sent_file, delivered_file, failed_file, campaign_log


def strip_markdown(text: str) -> str:
    lines: List[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            lines.append("")
            continue

        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
        line = re.sub(r"\*(.*?)\*", r"\1", line)
        line = re.sub(r"`(.*?)`", r"\1", line)
        line = re.sub(r"^[-*+]\s+", "- ", line)
        lines.append(line)
    return "\n".join(lines).strip()


def render_body(template_text: str, lead: Dict[str, str], sender_name: str) -> str:
    values = {
        "app_name": APP_NAME,
        "version": VERSION,
        "sender_name": sender_name,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "email": lead.get("email", ""),
        "first_name": lead.get("first_name", ""),
        "last_name": lead.get("last_name", ""),
        "full_name": lead.get("full_name", ""),
        "company": lead.get("company", ""),
    }

    for key, value in values.items():
        template_text = template_text.replace("{" + key + "}", str(value))

    return strip_markdown(template_text)


def sanitize_sender_name(value: str, fallback: str = "Microsoft Azure CLI") -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        return fallback

    cleaned = re.sub(r"\s+", " ", cleaned)
    lowered = cleaned.lower()
    if any(token in lowered for token in ["localhost", "127.0.0", "0.0.0.0", "::1", "example.com", "unknown host"]):
        return fallback

    return cleaned


def pick_pdf_path(pdf_path: Path, send_index: int) -> Path:
    if not pdf_path.exists():
        return pdf_path

    if pdf_path.is_dir():
        pdf_files = sorted([candidate for candidate in pdf_path.iterdir() if candidate.is_file() and candidate.suffix.lower() == ".pdf"])
        if pdf_files:
            return pdf_files[send_index % len(pdf_files)]

    return pdf_path


def compute_pdf_hash(pdf_path: Path) -> str:
    if not pdf_path.exists():
        return ""
    return hashlib.sha256(pdf_path.read_bytes()).hexdigest()


def infer_name_and_company(email: str) -> Tuple[str, str, str]:
    if not email:
        return "", "", ""

    local_part = email.split("@", 1)[0].strip().lower()
    domain = email.split("@", 1)[1].strip().lower() if "@" in email else ""
    company = domain.split(".")[0] if domain else ""
    first_name = local_part.split(".")[0] if local_part else ""
    if not first_name:
        first_name = local_part
    return first_name, "", company


def parse_lead_line(line: str, line_number: int) -> Dict[str, str]:
    raw = line.strip()
    if not raw or raw.startswith("#"):
        raise ValueError("skip")

    if "<" in raw and ">" in raw:
        name_part, email_part = raw.split("<", 1)
        email = email_part.split(">", 1)[0].strip()
        name = name_part.strip()
        full_name = name
        first_name = name.split()[0] if name else ""
        last_name = " ".join(name.split()[1:]) if len(name.split()) > 1 else ""
        return {"email": email, "full_name": full_name, "first_name": first_name, "last_name": last_name, "company": ""}

    if "|" in raw:
        parts = [part.strip() for part in raw.split("|")]
    elif "," in raw:
        parts = [part.strip() for part in raw.split(",")]
    else:
        parts = [raw]

    if not parts:
        raise ValueError("skip")

    email = parts[0]
    full_name = parts[1] if len(parts) > 1 else ""
    company = parts[2] if len(parts) > 2 else ""

    if not full_name and not company:
        first_name, _, company = infer_name_and_company(email)
        return {"email": email, "full_name": full_name, "first_name": first_name, "last_name": "", "company": company}

    first_name = full_name.split()[0] if full_name else ""
    last_name = " ".join(full_name.split()[1:]) if len(full_name.split()) > 1 else ""

    return {"email": email, "full_name": full_name, "first_name": first_name, "last_name": last_name, "company": company}


def load_leads(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Leads file not found: {path}")

    leads: List[Dict[str, str]] = []
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            lead = parse_lead_line(line, idx)
        except ValueError:
            continue
        if lead.get("email"):
            leads.append(lead)
    return leads


def build_message(
    to_email: str,
    subject: str,
    body_text: str,
    sender_name: str,
    from_email: str,
    pdf_path: Path,
    mail_client: str,
    sender_host: str,
    authentication_results: str,
    attachment_hash: str,
) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{sender_name} <{from_email}>"
    message["To"] = to_email
    message["Reply-To"] = from_email
    message["X-Mailer"] = mail_client
    message["X-Priority"] = "3"
    message["X-MSMail-Priority"] = "Normal"
    message["X-Sender-Host"] = sender_host
    message["Authentication-Results"] = authentication_results
    message["X-Authentication-Results"] = authentication_results
    if attachment_hash:
        message["X-Attachment-Hash"] = attachment_hash
    message.set_content(body_text)

    if pdf_path.exists() and pdf_path.suffix.lower() == ".pdf":
        try:
            message.add_attachment(pdf_path.read_bytes(), maintype="application", subtype="pdf", filename=pdf_path.name)
        except Exception as exc:  # noqa: BLE001
            message.set_content(body_text + f"\n\n[Attachment unavailable: {exc}]")
    return message


def send_message(
    message: EmailMessage,
    host: str,
    port: int,
    username: str,
    password: str,
    auth_type: str = "login",
    access_token: str = "",
) -> None:
    if port == 465:
        server = smtplib.SMTP_SSL(host, port, timeout=20)
    else:
        server = smtplib.SMTP(host, port, timeout=20)
        server.starttls(context=ssl.create_default_context())

    server.ehlo()
    auth_type, auth_username, auth_secret = build_smtp_auth_payload(username, password, auth_type, access_token)
    if auth_type == "xoauth2":
        server.auth("XOAUTH2", lambda _: auth_secret.encode("utf-8"))
    else:
        server.login(auth_username, auth_secret)
    server.send_message(message)
    server.quit()


def append_line(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text + "\n")


def main() -> int:
    args = parse_args()
    base_dir = Path(__file__).resolve().parent
    config_path = (base_dir / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config)
    config_values = load_config_file(config_path)

    def resolve_setting(cli_value: str, env_key: str, config_key: str, fallback: str) -> str:
        if cli_value:
            return cli_value
        if env_key and os.getenv(env_key):
            return os.getenv(env_key, "")
        if config_key and config_key in config_values:
            return config_values[config_key]
        return fallback

    args.smtp_host = resolve_setting(args.smtp_host, "SMTP_HOST", "SMTP_HOST", "")
    args.smtp_port = resolve_setting(str(args.smtp_port), "SMTP_PORT", "SMTP_PORT", "587")
    args.smtp_user = resolve_setting(args.smtp_user, "SMTP_USER", "SMTP_USER", "")
    args.smtp_password = resolve_setting(args.smtp_password, "SMTP_PASSWORD", "SMTP_PASSWORD", "")
    args.from_email = resolve_setting(args.from_email, "FROM_EMAIL", "FROM_EMAIL", "")
    args.sender_name = resolve_setting(args.sender_name, "SENDER_NAME", "SENDER_NAME", "Microsoft Azure CLI")
    args.mail_client = resolve_setting(args.mail_client, "MAIL_CLIENT", "MAIL_CLIENT", "Microsoft Azure CLI")
    args.sender_host = resolve_setting(args.sender_host, "SENDER_HOST", "SENDER_HOST", "Microsoft Azure CLI")
    args.authentication_results = resolve_setting(args.authentication_results, "AUTHENTICATION_RESULTS", "AUTHENTICATION_RESULTS", "dkim=pass spf=pass dmarc=pass")
    args.throttle_seconds = float(resolve_setting(str(args.throttle_seconds), "THROTTLE_SECONDS", "THROTTLE_SECONDS", "0"))
    args.smtp_auth_type = resolve_setting(args.smtp_auth_type, "SMTP_AUTH_TYPE", "SMTP_AUTH_TYPE", "login")
    args.smtp_access_token = resolve_setting(args.smtp_access_token, "SMTP_ACCESS_TOKEN", "SMTP_ACCESS_TOKEN", "")

    out_dir = (base_dir / args.out_dir).resolve()
    logger = setup_logging(out_dir)
    sent_file, delivered_file, failed_file, campaign_log = ensure_outputs(out_dir)

    leads_path = (base_dir / args.leads).resolve() if not Path(args.leads).is_absolute() else Path(args.leads)
    template_path = (base_dir / args.body_template).resolve() if not Path(args.body_template).is_absolute() else Path(args.body_template)
    pdf_path = (base_dir / args.pdf).resolve() if not Path(args.pdf).is_absolute() else Path(args.pdf)

    if not template_path.exists():
        logger.error("Body template not found: %s", template_path)
        return 2

    if not pdf_path.exists():
        logger.warning("PDF attachment not found: %s", pdf_path)

    if not args.smtp_host or not args.smtp_user or not args.smtp_password or not args.from_email:
        if args.dry_run:
            logger.info("Dry run bypasses SMTP credential validation; continuing with rendered messages.")
            args.smtp_host = "localhost"
            args.smtp_user = "dryrun"
            args.smtp_password = "dryrun"
            args.from_email = "dryrun@example.com"
        else:
            logger.error("SMTP host, SMTP user, SMTP password, and from email are required. Use arguments or environment variables.")
            return 2

    hosts = [item.strip() for item in args.smtp_host.split(",") if item.strip()]
    ports_raw = [item.strip() for item in str(args.smtp_port).split(",") if item.strip()]
    ports = [int(item) for item in ports_raw]
    if not ports:
        ports = [587]

    if len(ports) == 1:
        ports = ports * len(hosts)
    elif len(ports) != len(hosts):
        logger.error("SMTP hosts and ports must be the same length or use a single port for all hosts.")
        return 2

    body_template = template_path.read_text(encoding="utf-8")
    leads = load_leads(leads_path)

    if not leads:
        logger.error("No leads found in %s", leads_path)
        return 2

    logger.info("%s v%s started", APP_NAME, VERSION)
    logger.info("Preparing %d email(s) using %d SMTP host(s)", len(leads), len(hosts))

    sender_name = sanitize_sender_name(args.sender_name)
    mail_client = sanitize_sender_name(args.mail_client, fallback="Microsoft Azure CLI")
    sender_host = sanitize_sender_name(args.sender_host, fallback="Microsoft Azure CLI")
    authentication_results = args.authentication_results.strip() or "dkim=pass spf=pass dmarc=pass"

    smtp_index = 0
    for index, lead in enumerate(leads, start=1):
        recipient = lead.get("email", "").strip()
        if not recipient:
            logger.warning("Skipping empty email on lead #%d", index)
            continue

        full_name = lead.get("full_name") or lead.get("first_name", "")
        body_text = render_body(body_template, lead, sender_name)
        subject = args.subject
        if "{first_name}" in subject or "{full_name}" in subject or "{company}" in subject:
            subject = subject.format(**lead)

        selected_pdf = pick_pdf_path(pdf_path, smtp_index)
        attachment_hash = compute_pdf_hash(selected_pdf) if selected_pdf.exists() else ""
        message = build_message(
            recipient,
            subject,
            body_text,
            sender_name,
            args.from_email,
            selected_pdf,
            mail_client,
            sender_host,
            authentication_results,
            attachment_hash,
        )
        host = hosts[smtp_index % len(hosts)]
        port = ports[smtp_index % len(ports)]
        smtp_index += 1

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info("[%d/%d] Sending to %s via %s:%s", index, len(leads), recipient, host, port)
        if selected_pdf.exists():
            logger.info("Using attachment %s (sha256=%s)", selected_pdf.name, attachment_hash[:12])

        if args.dry_run:
            logger.info("Dry run only. Email content rendered for %s", recipient)
            append_line(campaign_log, f"{timestamp} | DRYRUN | {recipient} | {sender_name}")
            continue

        success = False
        for attempt in range(len(hosts)):
            current_host = hosts[(smtp_index - 1 + attempt) % len(hosts)]
            current_port = ports[(smtp_index - 1 + attempt) % len(ports)] if len(ports) == len(hosts) else ports[0]
            try:
                send_message(
                    message,
                    current_host,
                    current_port,
                    args.smtp_user,
                    args.smtp_password,
                    auth_type=args.smtp_auth_type,
                    access_token=args.smtp_access_token,
                )
                success = True
                break
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Send attempt failed for %s using %s:%s with auth=%s -> %s",
                    recipient,
                    current_host,
                    current_port,
                    args.smtp_auth_type,
                    exc,
                )
                time.sleep(1)

        if success:
            status_line = f"{timestamp} | SENT | {recipient} | {sender_name} | {host}:{port}"
            append_line(sent_file, status_line)
            append_line(delivered_file, status_line)
            append_line(campaign_log, status_line)
            logger.info("Delivered to %s", recipient)
        else:
            err_line = f"{timestamp} | FAILED | {recipient} | {sender_name}"
            append_line(failed_file, err_line)
            logger.error("Failed to deliver to %s", recipient)

        if args.throttle_seconds > 0 and index < len(leads):
            time.sleep(args.throttle_seconds)

    logger.info("Finished. Results saved to %s", out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())

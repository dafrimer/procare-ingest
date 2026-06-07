"""Pluggable notification backends used when alerts fire.

Backend selected via env NOTIFY_BACKEND (log | webhook | smtp | apprise).
Multiple backends can be enabled by setting NOTIFY_BACKEND to a comma-list.
"""
import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Protocol

import httpx

logger = logging.getLogger(__name__)


class Notifier(Protocol):
    def send(self, title: str, body: str, severity: str) -> None: ...


class LogNotifier:
    def send(self, title: str, body: str, severity: str) -> None:
        level = {"info": logging.INFO, "warning": logging.WARNING, "critical": logging.ERROR}.get(severity, logging.WARNING)
        logger.log(level, "NOTIFY [%s] %s | %s", severity, title, body)


class WebhookNotifier:
    """POSTs JSON to a webhook (Discord, Slack, ntfy, Gotify, generic).

    Discord: pass the webhook URL; body is wrapped as {"content": ...}.
    Slack:   pass the webhook URL; body is wrapped as {"text": ...}.
    Generic: set NOTIFY_WEBHOOK_FORMAT=generic to send {severity,title,body}.
    ntfy:    set NOTIFY_WEBHOOK_FORMAT=ntfy; we POST the body as plain text
             with X-Title and X-Priority headers.
    """
    def __init__(self, url: str, fmt: str = "generic"):
        self.url = url
        self.fmt = fmt.lower()

    def send(self, title: str, body: str, severity: str) -> None:
        try:
            if self.fmt == "discord":
                payload = {"content": f"**[{severity.upper()}] {title}**\n{body}"}
                httpx.post(self.url, json=payload, timeout=10).raise_for_status()
            elif self.fmt == "slack":
                payload = {"text": f"*[{severity.upper()}] {title}*\n{body}"}
                httpx.post(self.url, json=payload, timeout=10).raise_for_status()
            elif self.fmt == "ntfy":
                priority = {"info": "2", "warning": "3", "critical": "5"}.get(severity, "3")
                httpx.post(self.url, content=body.encode(), headers={
                    "Title": title, "Priority": priority, "Tags": severity,
                }, timeout=10).raise_for_status()
            else:
                payload = {"severity": severity, "title": title, "body": body}
                httpx.post(self.url, json=payload, timeout=10).raise_for_status()
        except Exception as e:
            logger.error("webhook notify failed: %s", e)


class SmtpNotifier:
    def __init__(self):
        self.host = os.getenv("SMTP_HOST")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.user = os.getenv("SMTP_USER")
        self.password = os.getenv("SMTP_PASSWORD")
        self.from_addr = os.getenv("SMTP_FROM", self.user or "")
        self.to_addr = os.getenv("SMTP_TO", "")
        self.use_tls = os.getenv("SMTP_TLS", "true").lower() == "true"

    def send(self, title: str, body: str, severity: str) -> None:
        if not (self.host and self.to_addr):
            logger.warning("smtp notifier missing SMTP_HOST or SMTP_TO; skipping")
            return
        msg = EmailMessage()
        msg["Subject"] = f"[procare-ingest/{severity}] {title}"
        msg["From"] = self.from_addr
        msg["To"] = self.to_addr
        msg.set_content(body)
        try:
            with smtplib.SMTP(self.host, self.port, timeout=15) as s:
                if self.use_tls:
                    s.starttls()
                if self.user:
                    s.login(self.user, self.password or "")
                s.send_message(msg)
        except Exception as e:
            logger.error("smtp notify failed: %s", e)


class AppriseNotifier:
    """Optional. Reads URLs from APPRISE_URLS (comma-separated)."""
    def __init__(self, urls: str):
        import apprise
        self._ap = apprise.Apprise()
        for u in urls.split(","):
            u = u.strip()
            if u:
                self._ap.add(u)

    def send(self, title: str, body: str, severity: str) -> None:
        try:
            self._ap.notify(title=title, body=body)
        except Exception as e:
            logger.error("apprise notify failed: %s", e)


def build_notifiers() -> list[Notifier]:
    backends = [b.strip().lower() for b in os.getenv("NOTIFY_BACKEND", "log").split(",") if b.strip()]
    out: list[Notifier] = []
    for b in backends:
        if b == "log":
            out.append(LogNotifier())
        elif b == "webhook":
            url = os.getenv("NOTIFY_WEBHOOK_URL")
            fmt = os.getenv("NOTIFY_WEBHOOK_FORMAT", "generic")
            if url:
                out.append(WebhookNotifier(url, fmt))
            else:
                logger.warning("NOTIFY_BACKEND includes 'webhook' but NOTIFY_WEBHOOK_URL is unset")
        elif b == "smtp":
            out.append(SmtpNotifier())
        elif b == "apprise":
            urls = os.getenv("APPRISE_URLS", "")
            if urls:
                try:
                    out.append(AppriseNotifier(urls))
                except ImportError:
                    logger.warning("apprise package not installed; skipping")
        else:
            logger.warning("unknown NOTIFY_BACKEND value: %s", b)
    if not out:
        out.append(LogNotifier())
    return out


def dispatch(notifiers: list[Notifier], title: str, body: str, severity: str) -> None:
    for n in notifiers:
        try:
            n.send(title, body, severity)
        except Exception as e:
            logger.error("notifier %s raised: %s", type(n).__name__, e)
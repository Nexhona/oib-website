#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OiB – Oldtimer in Büren a.A. — Kontaktformular Backend.

Speichert jede Anfrage durabel als JSON-Lines (geht nie verloren) und versendet
sie best-effort per SMTP an info@o-i-b.ch. Ohne SMTP-Konfiguration wird nur
gespeichert – das Formular funktioniert trotzdem sofort. Mail ist ein reiner
Config-Upgrade (kein Code-Change) sobald die Zugangsdaten vorliegen.
"""
import json
import os
import re
import smtplib
import time
from collections import deque
from datetime import datetime, timezone
from email.message import EmailMessage

from flask import Flask, request, jsonify

APP_DIR = os.path.dirname(os.path.abspath(__file__))
MESSAGES_FILE = os.path.join(APP_DIR, "messages.jsonl")

SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_SSL = os.environ.get("SMTP_SSL", "").lower() in ("1", "true", "yes")  # implicit TLS (port 465)
MAIL_TO = os.environ.get("MAIL_TO", "info@o-i-b.ch")
MAIL_FROM = os.environ.get("MAIL_FROM", SMTP_USER or "noreply@o-i-b.ch")

app = Flask(__name__)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# simple in-memory per-IP rate limit: 5 requests / 10 min
_RATE = {}
_RATE_MAX = 5
_RATE_WINDOW = 600


def _client_ip():
    # cloudflared -> nginx set X-Forwarded-For; first hop is the real client
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.headers.get("Cf-Connecting-Ip") or request.remote_addr or "unknown"


def _rate_limited(ip):
    now = time.time()
    dq = _RATE.setdefault(ip, deque())
    while dq and now - dq[0] > _RATE_WINDOW:
        dq.popleft()
    if len(dq) >= _RATE_MAX:
        return True
    dq.append(now)
    return False


def _send_mail(name, email, subject, message):
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS):
        return False
    try:
        msg = EmailMessage()
        subj = subject.strip() if subject else "Neue Kontaktanfrage"
        msg["Subject"] = f"[OiB Webseite] {subj} — von {name}"
        msg["From"] = MAIL_FROM
        msg["To"] = MAIL_TO
        msg["Reply-To"] = email
        body = (
            f"Neue Nachricht über das Kontaktformular der OiB-Webseite:\n\n"
            f"Name:    {name}\n"
            f"E-Mail:  {email}\n"
            f"Betreff: {subject or '(kein Betreff)'}\n\n"
            f"Nachricht:\n{message}\n\n"
            f"----\nGesendet am {datetime.now().strftime('%d.%m.%Y %H:%M')} via o-i-b.ch\n"
        )
        msg.set_content(body)
        if SMTP_SSL:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20) as s:
                s.login(SMTP_USER, SMTP_PASS)
                s.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
                s.starttls()
                s.login(SMTP_USER, SMTP_PASS)
                s.send_message(msg)
        return True
    except Exception as e:  # noqa: BLE001
        app.logger.error("Mailversand fehlgeschlagen: %s", e)
        return False


@app.route("/api/contact/health")
def health():
    return jsonify({
        "ok": True,
        "service": "oib-contact",
        "mail_configured": bool(SMTP_HOST and SMTP_USER and SMTP_PASS),
        "mail_to": MAIL_TO,
    })


@app.route("/api/contact", methods=["POST"])
def contact():
    data = request.get_json(silent=True) or request.form

    # honeypot: real users never fill the hidden "website" field
    if (data.get("website") or "").strip():
        return jsonify({"ok": True, "message": "Danke! Ihre Nachricht wurde gesendet."})

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    subject = (data.get("subject") or "").strip()
    message = (data.get("message") or "").strip()

    if not name or not email or not message:
        return jsonify({"ok": False, "error": "Bitte füllen Sie Name, E-Mail und Nachricht aus."}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"ok": False, "error": "Bitte geben Sie eine gültige E-Mail-Adresse an."}), 400
    if len(message) > 5000 or len(name) > 200 or len(subject) > 200:
        return jsonify({"ok": False, "error": "Ihre Eingabe ist zu lang."}), 400

    ip = _client_ip()
    if _rate_limited(ip):
        return jsonify({"ok": False, "error": "Zu viele Anfragen. Bitte versuchen Sie es in einigen Minuten erneut."}), 429

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "name": name,
        "email": email,
        "subject": subject,
        "message": message,
        "ip": ip,
        "ua": request.headers.get("User-Agent", "")[:300],
    }
    try:
        with open(MESSAGES_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:  # noqa: BLE001
        app.logger.error("Speichern fehlgeschlagen: %s", e)
        return jsonify({"ok": False, "error": "Serverfehler. Bitte später erneut versuchen."}), 500

    sent = _send_mail(name, email, subject, message)
    msg = "Danke! Ihre Nachricht wurde gesendet."
    if not sent and not (SMTP_HOST and SMTP_USER):
        # still stored — fine; user reads via nachrichten.py
        msg = "Danke! Ihre Nachricht wurde erfasst. Wir melden uns bei Ihnen."
    return jsonify({"ok": True, "message": msg})


if __name__ == "__main__":
    port = int(os.environ.get("OIB_CONTACT_PORT", "5055"))
    app.run(host="127.0.0.1", port=port)

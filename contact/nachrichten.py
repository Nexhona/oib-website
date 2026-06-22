#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Liest die gespeicherten Kontaktanfragen schön formatiert aus."""
import json
import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
MESSAGES_FILE = os.path.join(APP_DIR, "messages.jsonl")


def main():
    if not os.path.exists(MESSAGES_FILE):
        print("Noch keine Nachrichten vorhanden.")
        return
    with open(MESSAGES_FILE, encoding="utf-8") as f:
        lines = [l for l in f if l.strip()]
    if not lines:
        print("Noch keine Nachrichten vorhanden.")
        return
    print(f"\n{'='*64}\n  {len(lines)} Kontaktanfrage(n) — OiB Webseite\n{'='*64}")
    for i, line in enumerate(lines, 1):
        try:
            m = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = m.get("ts", "")[:19].replace("T", " ")
        print(f"\n#{i}  {ts}  (IP {m.get('ip','?')})")
        print(f"  Von:     {m.get('name','')} <{m.get('email','')}>")
        if m.get("subject"):
            print(f"  Betreff: {m['subject']}")
        print(f"  ---\n  {m.get('message','').replace(chr(10), chr(10)+'  ')}")
    print(f"\n{'='*64}\n")


if __name__ == "__main__":
    sys.exit(main())

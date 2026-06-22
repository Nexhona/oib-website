# OiB – Oldtimer in Büren a.A.

Neugestaltete Website für den Verein **OiB – Oldtimer in Büren a.A.** mit
funktionierendem Kontaktformular. Ersetzt die bisherige Wix-Seite
([o-i-b.ch](https://www.o-i-b.ch/)) durch eine selbst gehostete, moderne,
videobasierte Single-Page-Site.

Live (Self-Hosted, Cloudflare-Tunnel): **https://oib.kolica.ch**

---

## Inhalt

| Bereich | Beschreibung |
|---|---|
| **Start (Hero)** | Full-Bleed-Hintergrundvideo vom Oldtimertreffen, Anmelde-CTA |
| **Das Treffen** | Beschreibung des Anlasses + Event-Karte (6. September 2026, 9–17 Uhr) |
| **Video** | Highlight-Reel (~52 s) vom Treffen mit Ton |
| **Höhepunkte** | Icon-Grid: was die Besucher erwartet |
| **Organisation (OK)** | Das Organisationskomitee mit Zuständigkeiten |
| **Verein** | Der Vorstand (6 Mitglieder) |
| **Galerie** | Anmelde-Flyer 2021–2026 mit Lightbox |
| **Kontakt** | Kontaktformular → Mail an info@o-i-b.ch |

## Projektstruktur

```
oib/
├── site/                     # Statische Website (nginx-Webroot)
│   ├── index.html            # Single-Page-Site
│   └── assets/
│       ├── oib-logo.png
│       ├── flyer-2021..2026.jpg
│       └── video/            # Web-optimierte Videos + Poster (hero-loop, highlight-reel)
├── contact/                  # Kontaktformular-Backend (Flask)
│   ├── app.py                # Speichert JSONL + best-effort SMTP an info@o-i-b.ch
│   ├── nachrichten.py        # Reader: gespeicherte Anfragen anzeigen
│   ├── requirements.txt
│   ├── .env.example          # SMTP-Vorlage (echte .env wird NICHT committet)
│   └── oib-contact.service   # systemd-Unit
├── oib-nginx.conf            # nginx-Server-Block (Port 8086 + /api/contact-Proxy)
└── .gitignore
```

> Hinweis: Roh-Schnittdateien (`video/source.mp4`, Thumbnails) und die
> fertig gerenderten Originale liegen lokal unter `video/` und sind per
> `.gitignore` ausgeschlossen. Im Repo sind nur die web-optimierten Videos
> unter `site/assets/video/`.

## Deployment (Raspberry Pi + nginx + Cloudflare Tunnel)

```bash
# 1. Website in den Webroot
sudo cp site/index.html /var/www/oib/
sudo cp -r site/assets /var/www/oib/
sudo chown -R www-data:www-data /var/www/oib

# 2. Kontakt-Backend (Flask) als systemd-Dienst
python3 -m venv contact/venv
contact/venv/bin/pip install -r contact/requirements.txt
sudo cp contact/oib-contact.service /etc/systemd/system/
sudo systemctl enable --now oib-contact

# 3. nginx + Tunnel-Ingress (oib.kolica.ch -> 127.0.0.1:8086)
sudo cp oib-nginx.conf /etc/nginx/sites-available/oib
sudo ln -s /etc/nginx/sites-available/oib /etc/nginx/sites-enabled/oib
sudo nginx -t && sudo systemctl reload nginx
```

## Kontaktformular – E-Mail aktivieren

Das Formular speichert jede Anfrage sofort dauerhaft (`messages.jsonl`) und
verschickt sie zusätzlich per Mail, sobald SMTP konfiguriert ist:

```bash
cp contact/.env.example contact/.env   # SMTP-Zugangsdaten eintragen
sudo systemctl restart oib-contact
```

Gespeicherte Anfragen lesen:

```bash
contact/venv/bin/python contact/nachrichten.py
```

## Credits

Design & Entwicklung Webseite / N. Kolica / [www.kolica.ch](https://www.kolica.ch)

Video-Aufnahmen: Oldtimertreffen OiB – Oldtimer in Büren a.A.

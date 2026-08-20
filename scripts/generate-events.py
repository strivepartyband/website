import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests


# ============================================================
# KONFIGURATION
# ============================================================

CALENDAR_ID = os.environ["GOOGLE_CALENDAR_ID"]
API_KEY = os.environ["GOOGLE_CALENDAR_API_KEY"]

SITE_URL = "https://strivepartyband.de"

EVENTS_DIR = Path("events")

IMAGE_URL = f"{SITE_URL}/bilder/bandbild1.webp"

ORGANIZER = {
    "@type": "Organization",
    "name": "STR!VE Partyband",
    "url": SITE_URL,
}

PERFORMER = {
    "@type": "PerformingGroup",
    "name": "STR!VE Partyband",
}


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def slugify(text):
    text = text.lower().strip()

    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)

    return text.strip("-")


def parse_datetime(value):
    """
    Google liefert entweder:
      dateTime: 2026-08-20T19:30:00+02:00
    oder:
      date: 2026-08-20
    """

    if not value:
        return None

    if "T" in value:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def format_date(dt):
    return dt.strftime("%d.%m.%Y")


def format_time(dt):
    return dt.strftime("%H:%M")


def clean_description(event):
    description = event.get("description", "")

    # HTML aus Google-Kalender-Beschreibungen entfernen
    description = re.sub(r"<[^>]+>", " ", description)

    # Mehrere Leerzeichen reduzieren
    description = re.sub(r"\s+", " ", description)

    return description.strip()


def get_location(event):
    location = event.get("location", "").strip()

    if location:
        return location

    return "Veranstaltungsort wird noch bekanntgegeben"


# ============================================================
# GOOGLE CALENDAR
# ============================================================

def get_events():
    now = datetime.now(timezone.utc)

    url = (
        "https://www.googleapis.com/calendar/v3/calendars/"
        + quote(CALENDAR_ID, safe="")
        + "/events"
    )

    params = {
        "key": API_KEY,
        "timeMin": now.isoformat(),
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": 50,
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    return response.json().get("items", [])


# ============================================================
# EVENT JSON-LD
# ============================================================

def build_event_schema(event, slug):
    start_raw = event.get("start", {}).get("dateTime")
    end_raw = event.get("end", {}).get("dateTime")

    start = parse_datetime(start_raw)
    end = parse_datetime(end_raw)

    if not start:
        return None

    schema = {
        "@context": "https://schema.org",
        "@type": "Event",

        "name": event.get(
            "summary",
            "STR!VE Partyband"
        ),

        "startDate": start.isoformat(),

        "eventStatus": "https://schema.org/EventScheduled",

        "eventAttendanceMode":
            "https://schema.org/OfflineEventAttendanceMode",

        "location": {
            "@type": "Place",
            "name": get_location(event),
            "address": {
                "@type": "PostalAddress",
                "addressCountry": "DE"
            }
        },

        "image": [
            IMAGE_URL
        ],

        "description": clean_description(event)
        or "STR!VE Partyband live.",

        "organizer": ORGANIZER,

        "performer": PERFORMER,

        "url": f"{SITE_URL}/events/{slug}/",
    }

    if end:
        schema["endDate"] = end.isoformat()

    return schema


# ============================================================
# HTML
# ============================================================

def build_html(event, schema, slug):
    name = event.get("summary", "STR!VE Partyband")

    start = parse_datetime(
        event.get("start", {}).get("dateTime")
    )

    description = clean_description(event)
    location = get_location(event)

    schema_json = json.dumps(
        schema,
        ensure_ascii=False,
        indent=2
    )

    date_text = format_date(start)

    time_text = (
        format_time(start)
        if event.get("start", {}).get("dateTime")
        else "Zeit wird noch bekanntgegeben"
    )

    description_html = (
        description
        if description
        else "STR!VE Partyband live."
    )

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>{name} – STR!VE Partyband</title>

    <meta
        name="description"
        content="{description_html}"
    >

    <link
        rel="canonical"
        href="{SITE_URL}/events/{slug}/"
    >

    <script type="application/ld+json">
{schema_json}
    </script>

    <style>
        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            font-family: Arial, sans-serif;
            background: #111;
            color: #fff;
        }}

        main {{
            max-width: 900px;
            margin: 0 auto;
            padding: 80px 24px;
        }}

        .tag {{
            display: inline-block;
            color: #f5c800;
            font-size: 12px;
            font-weight: 800;
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-bottom: 20px;
        }}

        h1 {{
            margin: 0 0 24px;
            font-size: clamp(32px, 6vw, 64px);
            line-height: 1.05;
        }}

        .event-image {{
            width: 100%;
            height: auto;
            display: block;
            margin: 30px 0;
        }}

        .event-info {{
            display: grid;
            gap: 12px;
            margin: 30px 0;
            font-size: 18px;
        }}

        .event-description {{
            line-height: 1.7;
            color: #ccc;
        }}

        a {{
            color: #f5c800;
        }}

        .back {{
            display: inline-block;
            margin-top: 35px;
            text-decoration: none;
            font-weight: 700;
        }}
    </style>
</head>

<body>

<main>

    <div class="tag">STR!VE LIVE</div>

    <h1>{name}</h1>

    <img
        class="event-image"
        src="{IMAGE_URL}"
        alt="STR!VE Partyband"
        width="1200"
        height="800"
    >

    <div class="event-info">

        <div>
            <strong>Datum:</strong>
            {date_text}
        </div>

        <div>
            <strong>Beginn:</strong>
            {time_text} Uhr
        </div>

        <div>
            <strong>Ort:</strong>
            {location}
        </div>

    </div>

    <div class="event-description">
        {description_html}
    </div>

    <a class="back" href="{SITE_URL}/">
        ← Zurück zu STR!VE
    </a>

</main>

</body>
</html>
"""


# ============================================================
# SITEMAP
# ============================================================

def build_sitemap(slugs):
    urls = [
        f"{SITE_URL}/"
    ]

    urls.extend(
        f"{SITE_URL}/events/{slug}/"
        for slug in slugs
    )

    entries = "\n".join(
        f"""    <url>
        <loc>{url}</loc>
    </url>"""
        for url in urls
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset
    xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">

{entries}

</urlset>
"""


# ============================================================
# MAIN
# ============================================================

def main():
    print("Lade Google Kalender...")

    events = get_events()

    print(f"{len(events)} Termine gefunden.")

    EVENTS_DIR.mkdir(parents=True, exist_ok=True)

    # Alte automatisch erzeugte Event-Seiten entfernen
    for child in EVENTS_DIR.iterdir():
        if child.is_dir():
            shutil.rmtree(child)

    generated_slugs = []

    for event in events:

        # Nur öffentliche Termine
        visibility = event.get("visibility", "default")

        if visibility == "private":
            continue

        summary = event.get("summary")

        if not summary:
            continue

        start_raw = event.get("start", {}).get("dateTime")

        if not start_raw:
            # Ganztägige Events werden ebenfalls unterstützt,
            # aber ohne Uhrzeit.
            start_raw = event.get("start", {}).get("date")

        if not start_raw:
            continue

        slug_base = slugify(summary)

        if not slug_base:
            slug_base = "strive-event"

        start = parse_datetime(start_raw)

        slug = f"{slug_base}-{start.year}"

        # Kollisionen vermeiden
        original_slug = slug
        counter = 2

        while slug in generated_slugs:
            slug = f"{original_slug}-{counter}"
            counter += 1

        schema = build_event_schema(event, slug)

        if not schema:
            continue

        event_dir = EVENTS_DIR / slug
        event_dir.mkdir(parents=True, exist_ok=True)

        html = build_html(
            event,
            schema,
            slug
        )

        (event_dir / "index.html").write_text(
            html,
            encoding="utf-8"
        )

        generated_slugs.append(slug)

        print(f"Erzeugt: /events/{slug}/")

    sitemap = build_sitemap(generated_slugs)

    Path("sitemap.xml").write_text(
        sitemap,
        encoding="utf-8"
    )

    print()
    print(
        f"{len(generated_slugs)} Event-Seiten erzeugt."
    )
    print("sitemap.xml aktualisiert.")


if __name__ == "__main__":
    main()

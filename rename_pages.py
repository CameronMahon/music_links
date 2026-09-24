"""Renames site/page_id_*.html to descriptive slugs and rewrites internal links."""
import glob
import os
import re

SITE_DIR = os.path.join(os.path.dirname(__file__), "site")

NAME_MAP = {
    "page_id_17.html": "booking.html",
    "page_id_1911.html": "calendar.html",
    "page_id_2023.html": "orpheus-male-choir.html",
    "page_id_2119.html": "post-together-again-2022.html",
    "page_id_2202.html": "post-music-in-the-air-2022.html",
    "page_id_24.html": "history.html",
    "page_id_2478.html": "post-from-love-to-light.html",
    "page_id_2489.html": "post-community-in-song.html",
    "page_id_2497.html": "rehearsal-links.html",
    "page_id_335.html": "donate.html",
    "page_id_437.html": "advertising.html",
    "page_id_56.html": "events.html",
    "page_id_58.html": "music.html",
    "page_id_6.html": "contact-us.html",
    "page_id_63.html": "join.html",
}

# rewrite references (a href="page_id_17.html" etc.) in every html file
html_files = glob.glob(os.path.join(SITE_DIR, "*.html"))
for f in html_files:
    with open(f, encoding="utf-8") as fh:
        content = fh.read()
    new_content = content
    for old, new in NAME_MAP.items():
        new_content = re.sub(re.escape(old), new, new_content)
    if new_content != content:
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(new_content)

# rename the files themselves
for old, new in NAME_MAP.items():
    old_path = os.path.join(SITE_DIR, old)
    new_path = os.path.join(SITE_DIR, new)
    if os.path.exists(old_path):
        os.replace(old_path, new_path)

print("Renamed", len(NAME_MAP), "files")

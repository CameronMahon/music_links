"""
Mirrors the public pages of https://www.schneidermalechorus.ca/ into ./site
as static HTML + assets, rewriting internal links to relative local paths.

Only crawls the public WordPress front-end (login-protected member pages,
like Rehearsal Links / Calendar, are not reachable this way and should stay
as the manually saved copies already in this repo).
"""
import os
import re
import time
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

BASE = "https://www.schneidermalechorus.ca"
ALLOWED_HOSTS = {"www.schneidermalechorus.ca", "schneidermalechorus.ca"}
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "site")
MAX_PAGES = 60
SLEEP_SECONDS = 0.4

SKIP_SUBSTRINGS = (
    "/wp-login", "/wp-admin", "/wp-json", "/feed", "replytocom=",
    "action=", "wp-comments-post", "xmlrpc.php", "attachment_id=",
)

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (site-mirror-script; +personal backup)"})

visited_pages = set()
asset_cache = set()
url_to_local = {}  # full URL -> local relative path (for rewriting links)
queue = [BASE + "/"]


def is_internal(url):
    host = urlparse(url).netloc
    return host == "" or host in ALLOWED_HOSTS


def should_skip(url):
    return any(s in url for s in SKIP_SUBSTRINGS)


def normalize(url):
    url, _ = url, None
    parsed = urlparse(url)
    parsed = parsed._replace(fragment="")
    return urlunparse(parsed)


def local_path_for_page(url):
    parsed = urlparse(url)
    path = parsed.path
    if not path or path == "/":
        base_name = "index"
        subdir = ""
    else:
        subdir, last = os.path.split(path.strip("/"))
        base_name = last or "index"
        subdir = subdir
    if parsed.query:
        safe_query = re.sub(r"[^a-zA-Z0-9]+", "_", parsed.query).strip("_")
        base_name = f"{base_name}_{safe_query}" if base_name != "index" else safe_query or "index"
    if not base_name.endswith(".html"):
        base_name += ".html"
    return os.path.join(subdir, base_name)


def local_path_for_asset(url):
    parsed = urlparse(url)
    path = parsed.path.lstrip("/")
    if not path:
        path = "asset"
    return path


def fetch(url):
    try:
        resp = session.get(url, timeout=20)
        resp.raise_for_status()
        return resp
    except requests.RequestException as exc:
        print(f"  ! failed: {url} ({exc})")
        return None


def save_bytes(rel_path, content):
    full_path = os.path.join(OUTPUT_DIR, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "wb") as f:
        f.write(content)


def download_asset(url):
    url = normalize(url)
    if url in asset_cache or not is_internal(url) or should_skip(url):
        return
    asset_cache.add(url)
    resp = fetch(url)
    if resp is None:
        return
    rel_path = local_path_for_asset(url)
    save_bytes(rel_path, resp.content)
    url_to_local[url] = rel_path.replace(os.sep, "/")
    time.sleep(SLEEP_SECONDS)


def rel_link(from_rel_path, to_rel_path):
    from_dir = os.path.dirname(from_rel_path)
    rel = os.path.relpath(to_rel_path, from_dir or ".")
    return rel.replace(os.sep, "/")


pages_content = {}  # rel_path -> (soup, page_url)

print(f"Crawling {BASE} ...")
while queue and len(visited_pages) < MAX_PAGES:
    url = normalize(queue.pop(0))
    if url in visited_pages or not is_internal(url) or should_skip(url):
        continue
    visited_pages.add(url)
    print(f"[{len(visited_pages)}] page: {url}")
    resp = fetch(url)
    if resp is None or "text/html" not in resp.headers.get("Content-Type", ""):
        continue

    soup = BeautifulSoup(resp.text, "html.parser")
    rel_path = local_path_for_page(url).replace(os.sep, "/")
    url_to_local[url] = rel_path
    pages_content[rel_path] = (soup, url)

    # queue internal page links
    for a in soup.find_all("a", href=True):
        link = normalize(urljoin(url, a["href"]))
        if is_internal(link) and not should_skip(link) and link not in visited_pages:
            queue.append(link)

    # download assets referenced on this page
    for tag, attr in (("link", "href"), ("script", "src"), ("img", "src")):
        for el in soup.find_all(tag):
            src = el.get(attr)
            if src:
                download_asset(urljoin(url, src))

    time.sleep(SLEEP_SECONDS)

# rewrite internal links/assets to local relative paths
for rel_path, (soup, page_url) in pages_content.items():
    for tag, attr in (("a", "href"), ("link", "href"), ("script", "src"), ("img", "src")):
        for el in soup.find_all(tag):
            src = el.get(attr)
            if not src:
                continue
            abs_url = normalize(urljoin(page_url, src))
            local = url_to_local.get(abs_url)
            if local:
                el[attr] = rel_link(rel_path, local)
    save_bytes(rel_path, soup.prettify(formatter="html5").encode("utf-8"))

print(f"\nDone. {len(pages_content)} pages, {len(asset_cache)} assets saved under {OUTPUT_DIR}")

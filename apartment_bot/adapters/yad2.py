import asyncio
import json
import re
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

import nodriver as uc
from nodriver.core.config import Config

from apartment_bot.adapters.base import Listing, SourceAdapter

NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)
PROFILE_DIR = str(Path(__file__).resolve().parent.parent.parent / ".yad2_browser_profile")
FEED_BUCKETS = ("private", "agency", "platinum", "booster")

CHROME_DEBUG_PORT = 9222
CHROME_LAUNCH_FLAGS = [
    "--remote-debugging-host=127.0.0.1",
    f"--remote-debugging-port={CHROME_DEBUG_PORT}",
    f"--user-data-dir={PROFILE_DIR}",
    "--no-first-run",
    "--no-default-browser-check",
    "--no-service-autorun",
    "--password-store=basic",
    "--homepage=about:blank",
    "--disable-dev-shm-usage",  # Docker's 64MB /dev/shm is too small for Chrome
    "--disable-gpu",            # no real GPU on the server VM
    "--no-sandbox",             # Chrome refuses to sandbox when run as root
    "about:blank",
]


def _chrome_executable() -> str:
    # Reuse nodriver's own cross-platform detection (Mac app bundle, or
    # /bin/chromium on Linux) instead of hardcoding a path per platform.
    return Config().browser_executable_path


def _wait_for_devtools(port: int, timeout: float = 40.0) -> None:
    """Block until Chrome's DevTools endpoint actually responds.

    nodriver's built-in launcher only retries this for ~2.5s before giving
    up with a misleading "Failed to connect to browser" error. On a slow
    shared-vCPU server, Chrome's cold start exceeds that budget even though
    Chrome is perfectly healthy - so we launch Chrome ourselves and wait
    here as long as it genuinely needs, then connect nodriver to it.
    """
    deadline = time.monotonic() + timeout
    url = f"http://127.0.0.1:{port}/json/version"
    last_err: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, OSError) as e:
            last_err = e
        time.sleep(0.3)
    raise TimeoutError(f"Chrome DevTools port {port} never opened within {timeout}s ({last_err})")


def _extract_next_data(html: str) -> dict | None:
    m = NEXT_DATA_RE.search(html)
    if not m:
        return None
    return json.loads(m.group(1))


def _clear_stale_chrome_locks(profile_dir: str) -> None:
    """Remove Chrome's Singleton* lock files before launching.

    We're always the only process using this profile directory, so any
    leftover lock is necessarily stale - Chrome only fails to clean these up
    when the previous run was killed rather than exited cleanly (container
    restart, `docker compose down`, OOM kill, etc.), which is routine in a
    long-running deployment. Without this, one ungraceful shutdown would
    permanently block every future launch that reuses this profile.
    """
    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        path = Path(profile_dir) / name
        if path.exists() or path.is_symlink():
            path.unlink()


def _add_page_param(url: str, page: int) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    query["page"] = [str(page)]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def _feed_item_to_listing(item: dict) -> Listing:
    token = item.get("token")
    address = item.get("address", {})
    house = address.get("house", {})
    parts = [
        address.get("street", {}).get("text"),
        str(house.get("number")) if house.get("number") else None,
        address.get("neighborhood", {}).get("text"),
        address.get("city", {}).get("text"),
    ]
    details = item.get("additionalDetails", {})
    coords = address.get("coords", {})
    return Listing(
        source="yad2",
        external_id=token,
        url=f"https://www.yad2.co.il/realestate/item/{token}",
        price=item.get("price"),
        rooms=details.get("roomsCount"),
        floor=house.get("floor"),
        sqm=details.get("squareMeter"),
        address=", ".join(p for p in parts if p),
        photo_url=item.get("metaData", {}).get("coverImage"),
        raw_text=" ".join(t["name"] for t in item.get("tags", []) if "name" in t),
        latitude=coords.get("lat"),
        longitude=coords.get("lon"),
    )


class Yad2Adapter(SourceAdapter):
    """Fetches Yad2 rental listings.

    Yad2 sits behind Radware bot-management: plain HTTP and normal browser
    automation (Playwright/patchright, headless or headed) get stuck on a
    perpetual JS challenge page. `nodriver` avoids the standard Chrome
    DevTools automation interface these blockers fingerprint, and MUST run
    headed (headless mode trips a separate, stricter ShieldSquare check).
    """

    name = "yad2"

    def __init__(self, search_url: str, max_pages: int = 3, detail_fetch_limit: int = 25):
        self.search_url = search_url
        self.max_pages = max_pages
        self.detail_fetch_limit = detail_fetch_limit

    def fetch_listings(self, known_urls: set[str] | None = None) -> list[Listing]:
        return uc.loop().run_until_complete(self._fetch_listings_async(known_urls or set()))

    async def _wait_for_next_data(self, page, timeout: int = 25) -> dict:
        elapsed = 0
        while elapsed < timeout:
            html = await page.get_content()
            data = _extract_next_data(html)
            if data is not None:
                return data
            await asyncio.sleep(1)
            elapsed += 1
        raise TimeoutError("Yad2 never returned real content (still bot-checking?)")

    @staticmethod
    def _collect_feed(feed: dict, out: dict[str, Listing]) -> None:
        for bucket in FEED_BUCKETS:
            for item in feed.get(bucket, []):
                token = item.get("token")
                if token and token not in out:
                    out[token] = _feed_item_to_listing(item)

    async def _fetch_listings_async(self, known_urls: set[str]) -> list[Listing]:
        _clear_stale_chrome_locks(PROFILE_DIR)
        # Launch Chrome ourselves and wait for its DevTools port to actually
        # be ready, then connect nodriver to the running instance. This avoids
        # nodriver's ~2.5s launch-and-connect race, which fails on slow
        # shared-vCPU servers where Chrome's cold start takes longer.
        proc = subprocess.Popen(
            [_chrome_executable(), *CHROME_LAUNCH_FLAGS],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        browser = None
        try:
            _wait_for_devtools(CHROME_DEBUG_PORT)
            browser = await uc.start(host="127.0.0.1", port=CHROME_DEBUG_PORT)
            listings: dict[str, Listing] = {}

            page = await browser.get(self.search_url)
            data = await self._wait_for_next_data(page)
            feed = data["props"]["pageProps"]["feed"]
            total_pages = min(self.max_pages, feed.get("pagination", {}).get("totalPages", 1))
            self._collect_feed(feed, listings)

            for page_num in range(2, total_pages + 1):
                p = await browser.get(_add_page_param(self.search_url, page_num))
                data = await self._wait_for_next_data(p)
                self._collect_feed(data["props"]["pageProps"]["feed"], listings)

            new_listings = [lst for lst in listings.values() if lst.url not in known_urls]
            for listing in new_listings[: self.detail_fetch_limit]:
                p = await browser.get(listing.url)
                data = await self._wait_for_next_data(p)
                queries = data["props"]["pageProps"].get("dehydratedState", {}).get("queries", [])
                if queries:
                    detail = queries[0]["state"]["data"]
                    listing.raw_text = detail.get("searchText") or listing.raw_text
                    listing.posted_date = (detail.get("dates") or {}).get("createdAt")

            return list(listings.values())
        finally:
            if browser is not None:
                try:
                    browser.stop()
                except Exception:
                    pass
            # We launched Chrome, so we're responsible for killing it - nodriver
            # won't, since it only connected to an existing instance.
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

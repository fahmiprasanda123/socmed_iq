"""
Live Social Media Web Scraper & Intelligence Service.
Fetches real, live profile metrics directly from Instagram, Threads, and TikTok
without requiring third-party API keys or login tokens.
Computes engagement analytics strictly from scraped data — no synthetic/fake data.
"""

from __future__ import annotations
import abc
import concurrent.futures
import datetime
import hashlib
import html
import logging
import os
import re
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Tuple
import requests
from bs4 import BeautifulSoup

import urllib.parse

from utils.helpers import clean_handle
from services.storage import storage_service

logger = logging.getLogger(__name__)


def _generate_dynamic_account_card(handle: str, avatar_url: str = "") -> str:
    """Generates a dynamic SVG card tailored to the handle as a placeholder image."""
    if avatar_url and ("cdninstagram.com" in avatar_url or "scontent" in avatar_url):
        return avatar_url
    # Sanitize handle for SVG
    safe_handle = re.sub(r"[^a-zA-Z0-9._]", "", handle)[:30]
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
      <defs>
        <linearGradient id="grad_{safe_handle}" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:#4F46E5;stop-opacity:1" />
          <stop offset="50%" style="stop-color:#7C3AED;stop-opacity:1" />
          <stop offset="100%" style="stop-color:#EC4899;stop-opacity:1" />
        </linearGradient>
      </defs>
      <rect width="600" height="400" fill="url(#grad_{safe_handle})"/>
      <circle cx="300" cy="170" r="48" fill="#FFFFFF" opacity="0.18"/>
      <text x="300" y="185" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif" font-size="38" font-weight="bold" fill="#FFFFFF" text-anchor="middle">📷</text>
      <text x="300" y="260" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif" font-size="24" font-weight="700" fill="#FFFFFF" text-anchor="middle">@{safe_handle}</text>
      <text x="300" y="295" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif" font-size="14" font-weight="500" fill="#E0E7FF" text-anchor="middle">Social Media Profile</text>
    </svg>"""
    encoded = urllib.parse.quote(svg)
    return f"data:image/svg+xml;utf8,{encoded}"


class BaseDataService(abc.ABC):
    """Abstract Base Class for Data Fetching and Benchmarking Services."""

    @abc.abstractmethod
    def fetch_account_data(
        self,
        platform: str,
        raw_account: str,
        start_date: datetime.date,
        end_date: datetime.date,
        enable_backfill: bool = True,
    ) -> Dict[str, Any]:
        """Fetch profile metadata and posts for an account."""
        pass

    def fetch_benchmark_dataset(
        self,
        platform: str,
        main_account: str,
        competitors: List[str],
        start_date: datetime.date,
        end_date: datetime.date,
        enable_backfill: bool = True,
    ) -> Dict[str, Any]:
        """Fetch benchmark dataset for main account and all competitor accounts."""
        if isinstance(start_date, datetime.datetime):
            start_date = start_date.date()
        if isinstance(end_date, datetime.datetime):
            end_date = end_date.date()

        cleaned_main = clean_handle(main_account)
        cleaned_competitors = [clean_handle(c) for c in competitors if clean_handle(c)]

        all_handles = []
        seen = set()
        for h in [cleaned_main] + cleaned_competitors:
            if h and h.lower() not in seen:
                all_handles.append(h)
                seen.add(h.lower())

        accounts_data = []
        # Use concurrent threading for ALL platforms when multiple accounts
        if len(all_handles) > 1:
            acc_map = {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(all_handles))) as executor:
                future_to_handle = {
                    executor.submit(
                        self.fetch_account_data,
                        platform=platform,
                        raw_account=handle,
                        start_date=start_date,
                        end_date=end_date,
                        enable_backfill=enable_backfill,
                    ): handle
                    for handle in all_handles
                }
                for future in concurrent.futures.as_completed(future_to_handle):
                    h = future_to_handle[future]
                    try:
                        acc_map[h] = future.result()
                    except Exception as e:
                        logger.error("Failed to fetch data for @%s: %s", h, e, exc_info=True)
                        acc_map[h] = {
                            "handle": h,
                            "display_name": h,
                            "platform": platform,
                            "avatar_url": _generate_dynamic_account_card(h),
                            "bio": f"Gagal mengambil data @{h}: {str(e)[:100]}",
                            "followers": 0,
                            "start_followers": 0,
                            "growth_rate_pct": 0.0,
                            "following": 0,
                            "total_posts_lifetime": 0,
                            "is_verified": False,
                            "historical_followers": [],
                            "posts": [],
                            "not_found": True,
                            "data_source": "Error",
                            "has_real_post_metrics": False,
                            "history_source": "none",
                        }
            for handle in all_handles:
                if handle in acc_map:
                    acc = acc_map[handle]
                    acc["is_main"] = (handle.lower() == cleaned_main.lower())
                    accounts_data.append(acc)
        else:
            for handle in all_handles:
                is_main = (handle.lower() == cleaned_main.lower())
                try:
                    acc = self.fetch_account_data(
                        platform=platform,
                        raw_account=handle,
                        start_date=start_date,
                        end_date=end_date,
                        enable_backfill=enable_backfill,
                    )
                except Exception as e:
                    logger.error("Failed to fetch data for @%s: %s", handle, e, exc_info=True)
                    acc = {
                        "handle": handle,
                        "display_name": handle,
                        "platform": platform,
                        "avatar_url": _generate_dynamic_account_card(handle),
                        "bio": f"Gagal mengambil data @{handle}: {str(e)[:100]}",
                        "followers": 0,
                        "start_followers": 0,
                        "growth_rate_pct": 0.0,
                        "following": 0,
                        "total_posts_lifetime": 0,
                        "is_verified": False,
                        "historical_followers": [],
                        "posts": [],
                        "not_found": True,
                        "data_source": "Error",
                        "has_real_post_metrics": False,
                        "history_source": "none",
                    }
                acc["is_main"] = is_main
                accounts_data.append(acc)

        days_count = max(1, (end_date - start_date).days + 1)
        return {
            "platform": platform,
            "main_account": cleaned_main,
            "competitors": cleaned_competitors,
            "date_range": {
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d"),
                "days": days_count,
            },
            "accounts": accounts_data,
        }


class LiveWebScraperService(BaseDataService):
    """
    Live Social Media Scraper.
    Extracts real followers, following, posts count, bio, title, and avatars
    directly from public endpoints, then computes benchmark metrics
    strictly from scraped data.
    """

    # Realistic browser User-Agent for standard page requests
    DEFAULT_UA = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    # Social crawler User-Agent that receives full OpenGraph metadata without JS/login redirection
    CRAWLER_UA = "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"

    def __init__(self, *args, enable_backfill: bool = True, **kwargs):
        self.enable_backfill = enable_backfill
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.DEFAULT_UA,
            "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        # Check for proxy configuration from environment or Streamlit Secrets
        proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
        try:
            import streamlit as _st
            if not proxy and hasattr(_st, "secrets") and "PROXY_URL" in _st.secrets:
                proxy = str(_st.secrets["PROXY_URL"]).strip()
        except Exception:
            pass

        self.proxy = proxy
        if proxy:
            self.session.proxies = {
                "http": proxy,
                "https": proxy,
            }
            logger.info("LiveWebScraperService initialized with proxy: %s", proxy.split("@")[-1])

    def _parse_compact_number(self, s: str) -> int:
        """Parse numbers with k/m/b/rb/jt suffixes like 5,598, 95.7m, 12,4k, 2,5 jt."""
        if not s:
            return 0
        clean = s.strip().replace(" ", "").lower()
        clean = clean.replace("rb", "k").replace("jt", "m").replace("milyar", "b")
        try:
            # If comma is followed by digits and a suffix (e.g. 5,5m or 12,4k), it's a decimal comma
            if re.search(r",\d+[kmb]", clean):
                clean = clean.replace(",", ".")
            else:
                # Thousands separator
                clean = clean.replace(",", "")

            if "k" in clean:
                return int(float(clean.replace("k", "")) * 1_000)
            if "m" in clean:
                return int(float(clean.replace("m", "")) * 1_000_000)
            if "b" in clean:
                return int(float(clean.replace("b", "")) * 1_000_000_000)
            return int(float(clean))
        except (ValueError, TypeError):
            return 0

    def _scrape_instagram_profile(self, handle: str) -> Dict[str, Any]:
        """Scrapes live Instagram profile metadata via OG tags."""
        url = f"https://www.instagram.com/{handle}/"
        try:
            r = self.session.get(url, headers={"User-Agent": self.CRAWLER_UA}, timeout=10)
            # Check for redirect to login (Meta bot block on datacenter IPs like Streamlit Cloud / AWS)
            if r.history or "/accounts/login" in r.url:
                logger.warning("Instagram profile @%s redirected to login checkpoint (Datacenter IP block)", handle)
                return {"success": False, "handle": handle, "reason": "blocked_by_platform", "status_code": 302}

            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                og_desc = soup.find("meta", {"property": "og:description"})
                og_title = soup.find("meta", {"property": "og:title"})
                og_image = soup.find("meta", {"property": "og:image"})
                meta_desc = soup.find("meta", {"name": "description"})

                desc = html.unescape(og_desc.get("content", "")) if og_desc else ""
                title = html.unescape(og_title.get("content", "")) if og_title else ""
                avatar = html.unescape(og_image.get("content", "")) if og_image else ""

                # Example: 5,598 Followers, 107 Following, 440 Posts
                m_stats = re.search(
                    r"([\d,\.kmKM]+)\s+Followers?,\s+([\d,\.kmKM]+)\s+Following,\s+([\d,\.kmKM]+)\s+Posts",
                    desc,
                    re.I,
                )
                followers = self._parse_compact_number(m_stats.group(1)) if m_stats else 0
                following = self._parse_compact_number(m_stats.group(2)) if m_stats else 0
                total_posts = self._parse_compact_number(m_stats.group(3)) if m_stats else 0

                display_name = handle
                if og_title:
                    m_name = re.match(r"^(.*?)\s*\(\s*[@&#064;]+", title)
                    if m_name:
                        display_name = m_name.group(1).strip()

                bio = ""
                if meta_desc and meta_desc.get("content"):
                    c = html.unescape(meta_desc.get("content", ""))
                    if "on Instagram:" in c:
                        bio = c.split("on Instagram:", 1)[1].strip().strip('"')

                if followers > 0 or total_posts > 0:
                    return {
                        "success": True,
                        "handle": handle,
                        "display_name": display_name,
                        "followers": followers,
                        "following": following,
                        "total_posts": total_posts,
                        "bio": bio,
                        "avatar_url": avatar,
                    }
                else:
                    # Received HTTP 200 but blank/anti-bot challenge payload
                    logger.warning("Instagram profile @%s returned HTTP 200 without follower stats (challenge/blocked)", handle)
                    return {"success": False, "handle": handle, "reason": "blocked_by_platform", "status_code": 200}
            elif r.status_code == 404:
                logger.info("Instagram profile @%s returned 404", handle)
                return {"success": False, "handle": handle, "reason": "not_found", "status_code": 404}
            else:
                logger.warning("Instagram profile @%s returned HTTP %d", handle, r.status_code)
                is_block = r.status_code in (429, 403, 302)
                return {
                    "success": False,
                    "handle": handle,
                    "reason": "blocked_by_platform" if is_block else f"http_{r.status_code}",
                    "status_code": r.status_code,
                }
        except requests.RequestException as e:
            logger.error("Network error scraping Instagram @%s: %s", handle, e)
            return {"success": False, "handle": handle, "reason": "network_error"}
        except Exception as e:
            logger.error("Unexpected error scraping Instagram @%s: %s", handle, e, exc_info=True)
            return {"success": False, "handle": handle, "reason": "error"}

    def _get_chrome_path(self) -> Optional[str]:
        """Locates the Google Chrome or Chromium executable on the system."""
        candidate_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
        ]
        for p in candidate_paths:
            if os.path.exists(p) and os.access(p, os.X_OK):
                return p
        for bin_name in ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]:
            found = shutil.which(bin_name)
            if found:
                return found
        return None

    def _scrape_instagram_with_chrome(self, handle: str) -> Optional[Dict[str, Any]]:
        """
        Executes headless Chrome with --dump-dom to retrieve the fully-rendered client-side DOM.
        This provides real CDN image URLs, genuine post links (/p/{shortcode}/), real dates, and real captions.
        """
        chrome_path = self._get_chrome_path()
        if not chrome_path:
            return None

        # Validate handle to prevent shell injection — only allow safe characters
        if not re.match(r"^[a-zA-Z0-9._]+$", handle):
            logger.warning("Unsafe handle rejected for Chrome scraping: %s", handle)
            return None

        url = f"https://www.instagram.com/{handle}/"
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tf:
                tmp_path = tf.name

            # Use list args (no shell) to prevent command injection
            cmd = [
                chrome_path,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-extensions",
                "--virtual-time-budget=6000",
                f"--user-agent={self.DEFAULT_UA}",
                "--dump-dom",
            ]
            if getattr(self, "proxy", None):
                cmd.append(f"--proxy-server={self.proxy}")
            cmd.append(url)

            with open(tmp_path, "w", encoding="utf-8") as outfile:
                res = subprocess.run(
                    cmd,
                    stdout=outfile,
                    stderr=subprocess.PIPE,
                    timeout=25,
                )
            if res.returncode != 0:
                stderr_text = ""
                if res.stderr:
                    stderr_text = res.stderr.decode("utf-8", errors="replace")[:200]
                logger.warning("Chrome dump-dom failed for @%s (exit %d): %s", handle, res.returncode, stderr_text)
                return None

            if not os.path.exists(tmp_path):
                return None

            with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                html_content = f.read()

            if len(html_content) < 5000:
                return None

            soup = BeautifulSoup(html_content, "html.parser")

            # 1. Profile metadata
            og_desc = soup.find("meta", {"property": "og:description"})
            og_title = soup.find("meta", {"property": "og:title"})
            og_image = soup.find("meta", {"property": "og:image"})
            meta_desc = soup.find("meta", {"name": "description"})

            desc = html.unescape(og_desc.get("content", "")) if og_desc else ""
            title = html.unescape(og_title.get("content", "")) if og_title else ""
            avatar = html.unescape(og_image.get("content", "")) if og_image else ""

            m_stats = re.search(
                r"([\d,\.kmKM]+)\s+Followers?,\s+([\d,\.kmKM]+)\s+Following,\s+([\d,\.kmKM]+)\s+Posts",
                desc,
                re.I,
            )
            followers = self._parse_compact_number(m_stats.group(1)) if m_stats else 0
            following = self._parse_compact_number(m_stats.group(2)) if m_stats else 0
            total_posts = self._parse_compact_number(m_stats.group(3)) if m_stats else 0

            display_name = handle
            if og_title:
                m_name = re.match(r"^(.*?)\s*\(\s*[@&#064;]+", title)
                if m_name:
                    display_name = m_name.group(1).strip()

            bio = ""
            if meta_desc and meta_desc.get("content"):
                c = html.unescape(meta_desc.get("content", ""))
                if "on Instagram:" in c:
                    bio = c.split("on Instagram:", 1)[1].strip().strip('"')

            # 2. Extract Real Posts: Primary extraction from Relay Preloader JSON (polaris_ordered_timeline_connection)
            seen_codes = set()
            raw_posts = []

            try:
                idx_timeline = html_content.find("polaris_ordered_timeline_connection")
                if idx_timeline != -1:
                    start_s = html_content.rfind("<script", 0, idx_timeline)
                    end_s = html_content.find("</script>", idx_timeline)
                    if start_s != -1 and end_s != -1:
                        script_body = html_content[start_s:end_s].split(">", 1)[1]
                        relay_json = json.loads(script_body)

                        def _extract_timeline_edges(obj):
                            if isinstance(obj, dict):
                                if "polaris_ordered_timeline_connection" in obj:
                                    return obj["polaris_ordered_timeline_connection"].get("edges", [])
                                for v in obj.values():
                                    res = _extract_timeline_edges(v)
                                    if res:
                                        return res
                            elif isinstance(obj, list):
                                for item in obj:
                                    res = _extract_timeline_edges(item)
                                    if res:
                                        return res
                            return []

                        edges = _extract_timeline_edges(relay_json)
                        for edge in edges:
                            node = edge.get("node", {})
                            code = node.get("code")
                            if code and code not in seen_codes:
                                seen_codes.add(code)
                                cap_data = node.get("caption")
                                cap_text = ""
                                if isinstance(cap_data, dict):
                                    cap_text = cap_data.get("text", "")
                                elif isinstance(cap_data, str):
                                    cap_text = cap_data

                                typename = node.get("__typename", "")
                                content_type = (
                                    "Carousel"
                                    if "Carousel" in typename
                                    else ("Reels/Video" if ("Video" in typename or "Clip" in typename) else "Single Image")
                                )
                                raw_posts.append({
                                    "shortcode": code,
                                    "post_url": f"https://www.instagram.com/p/{code}/",
                                    "thumbnail_url": node.get("display_uri") or "",
                                    "alt": node.get("accessibility_caption") or "",
                                    "caption": cap_text,
                                    "content_type": content_type,
                                })
            except Exception as e_json:
                logger.debug("Error parsing polaris timeline JSON: %s", e_json)

            # Secondary fallback: Extract from standard <a> anchor tags in rendered DOM
            if not raw_posts:
                links = soup.find_all("a", href=True)
                for a in links:
                    href = a.get("href", "")
                    m = re.search(r"/(?:p|reel)/([A-Za-z0-9_-]+)", href)
                    if not m:
                        continue
                    code = m.group(1)
                    if code in seen_codes:
                        continue

                    # If the link has an account prefix, verify it belongs to handle
                    m_owner = re.search(r"^/([^/]+)/(?:p|reel)/", href)
                    if m_owner:
                        owner = m_owner.group(1).lower()
                        if owner != handle.lower() and owner not in ["p", "reel"]:
                            continue

                    seen_codes.add(code)

                    img = a.find("img")
                    img_src = img.get("src", "") if img else ""
                    img_alt = img.get("alt", "") if img else ""

                    if not img_src:
                        continue

                    raw_posts.append({
                        "shortcode": code,
                        "post_url": f"https://www.instagram.com/p/{code}/",
                        "thumbnail_url": img_src,
                        "alt": img_alt,
                    })

            return {
                "success": True,
                "handle": handle,
                "display_name": display_name,
                "followers": followers,
                "following": following,
                "total_posts": total_posts,
                "bio": bio,
                "avatar_url": avatar,
                "scraped_posts": raw_posts,
            }
        except subprocess.TimeoutExpired:
            logger.warning("Chrome timed out for @%s", handle)
            return None
            return None
        except Exception as e:
            logger.error("Chrome scraping error for @%s: %s", handle, e, exc_info=True)
            return None
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    def _parse_instagram_post_metadata(
        self,
        alt_text: str,
        shortcode: str,
        handle: str,
    ) -> Tuple[Optional[datetime.datetime], str, str, str]:
        """
        Extracts date, formatted date string, content format type, and caption
        from the post's rendered alt text.
        """
        # Extract date from alt string: e.g. "on September 11, 2026"
        m_date = re.search(r"on\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})", alt_text)
        post_dt = None
        date_str = ""
        if m_date:
            try:
                post_dt = datetime.datetime.strptime(m_date.group(1), "%B %d, %Y")
                date_str = post_dt.strftime("%d %b %Y")
            except Exception:
                pass

        # Format type
        is_video = alt_text.lower().startswith("video")
        is_carousel = "carousel" in alt_text.lower()
        content_type = "Reels/Video" if is_video else ("Carousel" if is_carousel else "Single Image")

        # Extract caption text from alt
        caption = ""
        m_text = re.search(r"text that says [\x27\u2018\u201c\"](.*?)[\x27\u2019\u201d\"]\s*\.?", alt_text, re.DOTALL)
        if m_text and len(m_text.group(1).strip()) > 3:
            caption = m_text.group(1).strip()
        else:
            if m_date:
                after = alt_text[m_date.end():].strip(" .")
                after = re.sub(
                    r"^(May be an image of|May be a graphic of|May be a photo of|May be a meme of)\s*",
                    "",
                    after,
                    flags=re.I,
                ).strip()
                if after and len(after) > 5:
                    caption = after.capitalize()

        return post_dt, date_str, content_type, caption

    def _fetch_instagram_post_metadata(self, shortcode: str) -> Optional[Dict[str, Any]]:
        """
        Fetches authentic, ground-truth post metrics (exact likes, comments, caption, date)
        directly from Instagram's canonical crawler metadata endpoint without login or API keys.
        """
        url = f"https://www.instagram.com/p/{shortcode}/"
        headers = {
            "User-Agent": self.CRAWLER_UA,
            "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        }
        try:
            r = self.session.get(url, headers=headers, timeout=12)
            if r.status_code != 200:
                return None
            soup = BeautifulSoup(r.text, "html.parser")
            og_desc = soup.find("meta", {"property": "og:description"})
            if not og_desc or not og_desc.get("content"):
                return None
            desc = html.unescape(og_desc.get("content", "")).strip()

            likes = 0
            comments = 0
            views = 0
            date_str = ""
            post_dt = None
            caption = ""

            # Check for likes count: e.g. "895 likes"
            m_likes = re.search(r"([\d,\.kmKM]+)\s+likes?", desc, re.I)
            if m_likes:
                likes = self._parse_compact_number(m_likes.group(1))

            # Check for comments count: e.g. "10 comments"
            m_comm = re.search(r"([\d,\.kmKM]+)\s+comments?", desc, re.I)
            if m_comm:
                comments = self._parse_compact_number(m_comm.group(1))

            # Check for views count: e.g. "12.5k views"
            m_views = re.search(r"([\d,\.kmKM]+)\s+views?", desc, re.I)
            if m_views:
                views = self._parse_compact_number(m_views.group(1))

            # Extract date: e.g. "on September 8, 2026"
            m_date = re.search(r"on\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})", desc, re.I)
            if m_date:
                raw_date = m_date.group(1).strip()
                try:
                    post_dt = datetime.datetime.strptime(raw_date, "%B %d, %Y")
                    date_str = post_dt.strftime("%d %b %Y")
                except Exception:
                    date_str = raw_date

            # Extract caption: text following the colon after date
            if m_date:
                colon_idx = desc.find(":", m_date.end())
                if colon_idx != -1:
                    raw_caption = desc[colon_idx + 1:].strip()
                    if (raw_caption.startswith('"') and raw_caption.endswith('"')) or (raw_caption.startswith("'") and raw_caption.endswith("'")):
                        raw_caption = raw_caption[1:-1].strip()
                    elif raw_caption.startswith('"'):
                        raw_caption = raw_caption.lstrip('"').rstrip('" .')
                    caption = raw_caption

            # Fallback to og:title if caption is still empty
            if not caption:
                og_title = soup.find("meta", {"property": "og:title"})
                if og_title and og_title.get("content"):
                    t_content = html.unescape(og_title.get("content", ""))
                    if ":" in t_content:
                        caption = t_content.split(":", 1)[1].strip(' ".\r\n')

            return {
                "success": True,
                "likes": likes,
                "comments": comments,
                "views": views,
                "date_str": date_str,
                "post_dt": post_dt,
                "caption": caption,
            }
        except requests.RequestException as e:
            logger.debug("Network error fetching post %s: %s", shortcode, e)
            return None
        except Exception as e:
            logger.debug("Error fetching post %s: %s", shortcode, e)
            return None

    def _scrape_threads_profile(self, handle: str) -> Dict[str, Any]:
        """Scrapes live Threads profile metadata."""
        url = f"https://www.threads.net/@{handle}"
        try:
            r = self.session.get(url, headers={"User-Agent": self.CRAWLER_UA}, timeout=10)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                og_desc = soup.find("meta", {"property": "og:description"})
                og_title = soup.find("meta", {"property": "og:title"})
                og_image = soup.find("meta", {"property": "og:image"})

                desc = html.unescape(og_desc.get("content", "")) if og_desc else ""
                title = html.unescape(og_title.get("content", "")) if og_title else ""
                avatar = html.unescape(og_image.get("content", "")) if og_image else ""

                followers = 0
                threads_count = 0
                bio = ""
                if desc:
                    parts = [p.strip() for p in desc.split("\u2022")]
                    for p in parts:
                        if "follower" in p.lower():
                            m = re.search(r"([\d,\.kmKM]+)", p)
                            if m:
                                followers = self._parse_compact_number(m.group(1))
                        elif "thread" in p.lower():
                            m = re.search(r"([\d,\.kmKM]+)", p)
                            if m:
                                threads_count = self._parse_compact_number(m.group(1))
                        elif "see the latest" not in p.lower():
                            bio = p

                display_name = handle
                if title:
                    m_name = re.match(r"^(.*?)\s*\(\s*[@&#064;]+", title)
                    if m_name:
                        display_name = m_name.group(1).strip()

                if followers > 0 or threads_count > 0:
                    return {
                        "success": True,
                        "handle": handle,
                        "display_name": display_name,
                        "followers": followers,
                        "following": 0,
                        "total_posts": threads_count,
                        "bio": bio,
                        "avatar_url": avatar,
                    }
                else:
                    return {"success": False, "handle": handle, "reason": "blocked_by_platform", "status_code": 200}
            elif r.status_code == 404:
                return {"success": False, "handle": handle, "reason": "not_found", "status_code": 404}
            else:
                is_block = r.status_code in (429, 403, 302)
                return {"success": False, "handle": handle, "reason": "blocked_by_platform" if is_block else f"http_{r.status_code}", "status_code": r.status_code}
        except requests.RequestException as e:
            logger.error("Network error scraping Threads @%s: %s", handle, e)
            return {"success": False, "handle": handle, "reason": "network_error"}
        except Exception as e:
            logger.error("Error scraping Threads @%s: %s", handle, e, exc_info=True)
            return {"success": False, "handle": handle, "reason": "error"}

    def _scrape_tiktok_profile(self, handle: str) -> Dict[str, Any]:
        """Scrapes live TikTok profile metadata."""
        url = f"https://www.tiktok.com/@{handle}"
        try:
            r = self.session.get(url, headers={"User-Agent": self.CRAWLER_UA}, timeout=10)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                og_desc = soup.find("meta", {"property": "og:description"})
                og_title = soup.find("meta", {"property": "og:title"})
                og_image = soup.find("meta", {"property": "og:image"})

                desc = html.unescape(og_desc.get("content", "")) if og_desc else ""
                title = html.unescape(og_title.get("content", "")) if og_title else ""
                avatar = html.unescape(og_image.get("content", "")) if og_image else ""

                m = re.search(r"([\d,\.kmKM]+)\s+Followers?,\s+([\d,\.kmKM]+)\s+Following,\s+([\d,\.kmKM]+)\s+Likes", desc, re.I)
                followers = self._parse_compact_number(m.group(1)) if m else 0
                following = self._parse_compact_number(m.group(2)) if m else 0

                # Try to extract video count from description
                m_videos = re.search(r"([\d,\.kmKM]+)\s+(?:Videos?|video)", desc, re.I)
                total_posts = self._parse_compact_number(m_videos.group(1)) if m_videos else 0

                display_name = handle
                if title:
                    display_name = title.replace("on TikTok", "").strip()

                if followers > 0:
                    return {
                        "success": True,
                        "handle": handle,
                        "display_name": display_name,
                        "followers": followers,
                        "following": following,
                        "total_posts": total_posts,
                        "bio": desc,
                        "avatar_url": avatar,
                    }
                else:
                    return {"success": False, "handle": handle, "reason": "blocked_by_platform", "status_code": 200}
            elif r.status_code == 404:
                return {"success": False, "handle": handle, "reason": "not_found", "status_code": 404}
            else:
                is_block = r.status_code in (429, 403, 302)
                return {"success": False, "handle": handle, "reason": "blocked_by_platform" if is_block else f"http_{r.status_code}", "status_code": r.status_code}
        except requests.RequestException as e:
            logger.error("Network error scraping TikTok @%s: %s", handle, e)
            return {"success": False, "handle": handle, "reason": "network_error"}
        except Exception as e:
            logger.error("Error scraping TikTok @%s: %s", handle, e, exc_info=True)
            return {"success": False, "handle": handle, "reason": "error"}

    def fetch_account_data(
        self,
        platform: str,
        raw_account: str,
        start_date: datetime.date,
        end_date: datetime.date,
        enable_backfill: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Executes live web scraping for the profile, then computes
        engagement analytics strictly from scraped data.
        Snapshots are automatically recorded to local SQLite DB for historical tracking.
        """
        handle = clean_handle(raw_account)
        platform_lower = platform.lower()

        if isinstance(start_date, datetime.datetime):
            start_date = start_date.date()
        if isinstance(end_date, datetime.datetime):
            end_date = end_date.date()

        # 1. Scrape live profile and real posts
        raw_scraped_posts = []
        if platform_lower == "threads":
            profile = self._scrape_threads_profile(handle)
        elif platform_lower == "tiktok":
            profile = self._scrape_tiktok_profile(handle)
        else:
            # 1. Fetch live profile metadata reliably via social crawler headers (< 1s)
            profile = self._scrape_instagram_profile(handle)
            # 2. Attempt Chrome headless dump-dom to extract rendered posts if available
            if self._get_chrome_path():
                chrome_result = self._scrape_instagram_with_chrome(handle)
                if chrome_result:
                    if chrome_result.get("scraped_posts"):
                        raw_scraped_posts = chrome_result["scraped_posts"]
                    if not profile.get("success") and chrome_result.get("success"):
                        profile = chrome_result

        # If profile was NOT found or was blocked
        if not profile.get("success"):
            is_blocked = profile.get("reason") in ("blocked_by_platform", "rate_limited")
            return {
                "handle": handle,
                "display_name": handle,
                "platform": platform,
                "avatar_url": _generate_dynamic_account_card(handle),
                "bio": f"Akses profil @{handle} dibatasi/diblokir oleh {platform} (IP Cloud Server/Rate Limit)." if is_blocked else f"Akun @{handle} tidak ditemukan di {platform}.",
                "followers": 0,
                "start_followers": 0,
                "growth_rate_pct": 0.0,
                "following": 0,
                "total_posts_lifetime": 0,
                "is_verified": False,
                "historical_followers": [],
                "posts": [],
                "not_found": not is_blocked,
                "is_blocked": is_blocked,
                "data_source": f"{platform} Membatasi Akses (Cloud IP Block)" if is_blocked else f"Akun @{handle} Tidak Ditemukan",
                "has_real_post_metrics": False,
                "history_source": "none",
            }

        followers = profile["followers"]
        following = profile["following"]
        total_posts_lifetime = max(0, profile["total_posts"])
        display_name = profile["display_name"]
        bio = profile["bio"]
        avatar_url = profile["avatar_url"] if profile.get("avatar_url") else _generate_dynamic_account_card(handle)
        source_tag = "Live Web Scraper (Chrome Headless)" if raw_scraped_posts else "Live Web Scraper (OG Tags)"

        days_count = max(1, (end_date - start_date).days + 1)

        # 2. Build posts list from REAL scraped data only — no fake posts
        posts = []
        has_real_post_metrics = False

        if raw_scraped_posts:
            # Parallel fetch ground-truth post metrics (exact likes, comments, caption, date)
            shortcodes = [r_post["shortcode"] for r_post in raw_scraped_posts]
            details_map = {}
            if shortcodes:
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(shortcodes))) as executor:
                    future_to_sc = {
                        executor.submit(self._fetch_instagram_post_metadata, sc): sc
                        for sc in shortcodes
                    }
                    for future in concurrent.futures.as_completed(future_to_sc):
                        sc = future_to_sc[future]
                        try:
                            res = future.result()
                            if res:
                                details_map[sc] = res
                        except Exception as e:
                            logger.debug("Failed to fetch post metadata %s: %s", sc, e)

            for idx, r_post in enumerate(raw_scraped_posts):
                shortcode = r_post["shortcode"]
                real_meta = details_map.get(shortcode)

                post_dt = real_meta.get("post_dt") if real_meta else None
                date_str = real_meta.get("date_str") if real_meta else ""
                caption = real_meta.get("caption") if real_meta and real_meta.get("caption") else ""

                alt_dt, alt_date_str, content_type, alt_caption = self._parse_instagram_post_metadata(
                    r_post.get("alt", ""), shortcode, handle
                )
                if not post_dt:
                    post_dt = alt_dt
                if not date_str:
                    date_str = alt_date_str

                # Prioritize scraped caption from relay/polaris or crawler metadata
                if not caption and r_post.get("caption"):
                    caption = r_post["caption"]
                if not caption:
                    caption = alt_caption
                if not caption:
                    caption = "Caption tidak tersedia."

                # Prioritize explicit content_type detected from relay media
                if r_post.get("content_type"):
                    content_type = r_post["content_type"]

                # Extract hashtags directly from caption
                hashtags = re.findall(r"#\w+", caption) if caption else []

                # Determine if post falls within date range
                in_date_range = True
                if post_dt:
                    post_date = post_dt.date()
                    in_date_range = (start_date <= post_date <= end_date)

                is_reel = "reel" in content_type.lower() or "video" in content_type.lower()

                # Use REAL metrics if available from Instagram
                if real_meta and real_meta.get("success", False):
                    likes = real_meta.get("likes", 0)
                    comments = real_meta.get("comments", 0)
                    views = real_meta.get("views", 0)
                    has_real_post_metrics = True
                    shares = 0
                    saves = 0
                    total_inter = likes + comments
                    post_er = round((total_inter / max(1, followers)) * 100.0, 2) if followers > 0 else 0.0
                    is_estimated = False
                elif real_meta and (real_meta.get("likes", 0) > 0 or real_meta.get("comments", 0) > 0):
                    likes = real_meta["likes"]
                    comments = real_meta["comments"]
                    views = real_meta.get("views", 0)
                    has_real_post_metrics = True
                    shares = 0
                    saves = 0
                    total_inter = likes + comments
                    post_er = round((total_inter / max(1, followers)) * 100.0, 2) if followers > 0 else 0.0
                    is_estimated = False
                else:
                    # No real metrics available — set to 0 and flag as estimated
                    likes = 0
                    comments = 0
                    shares = 0
                    saves = 0
                    total_inter = 0
                    post_er = 0.0
                    views = 0
                    is_estimated = True

                post_entry = {
                    "post_id": f"{handle}_{shortcode}",
                    "account": handle,
                    "date": date_str if date_str else "-",
                    "timestamp": post_dt.isoformat() if post_dt else "",
                    "day_of_week": post_dt.weekday() if post_dt else 0,
                    "hour": post_dt.hour if post_dt else 12,
                    "content_type": content_type,
                    "caption": caption,
                    "hashtags": hashtags,
                    "likes": likes,
                    "comments": comments,
                    "shares": shares,
                    "saves": saves,
                    "views": views,
                    "total_interactions": total_inter,
                    "post_er": post_er,
                    "thumbnail_url": r_post.get("thumbnail_url", ""),
                    "post_url": r_post.get("post_url", f"https://www.instagram.com/p/{shortcode}/"),
                    "is_estimated": is_estimated,
                    "in_date_range": in_date_range,
                }
                posts.append(post_entry)

        # 3. Snapshot persistence to local SQLite Database
        real_posts = [p for p in posts if not p.get("is_estimated", False)]
        avg_likes = sum(p.get("likes", 0) for p in real_posts) / max(1, len(real_posts)) if real_posts else 0.0
        avg_comments = sum(p.get("comments", 0) for p in real_posts) / max(1, len(real_posts)) if real_posts else 0.0
        avg_er = ((avg_likes + avg_comments) / max(1, followers)) * 100.0 if followers > 0 else 0.0

        storage_service.save_account_snapshot(
            platform=platform,
            handle=handle,
            followers=followers,
            following=following,
            total_posts=total_posts_lifetime,
            avg_likes=avg_likes,
            avg_comments=avg_comments,
            avg_er=avg_er,
            snapshot_date=end_date,
            source="scraper",
        )

        if posts:
            storage_service.save_posts_cache(platform, handle, posts)

        # Merge previously cached historical posts for earlier dates
        cached_db_posts = storage_service.get_cached_posts(platform, handle, start_date, end_date)
        if cached_db_posts:
            existing_urls = {p.get("post_url") for p in posts if p.get("post_url")}
            for cp in cached_db_posts:
                if cp.get("post_url") and cp["post_url"] not in existing_urls:
                    posts.append({
                        "post_id": cp.get("post_id", ""),
                        "shortcode": cp.get("post_id", ""),
                        "timestamp": cp.get("timestamp", ""),
                        "posted_at": cp.get("timestamp", "")[:10] if cp.get("timestamp") else "",
                        "content_type": cp.get("post_type", "Image"),
                        "caption": cp.get("caption", ""),
                        "likes": cp.get("likes", 0),
                        "comments": cp.get("comments", 0),
                        "shares": cp.get("shares", 0),
                        "saves": 0,
                        "views": cp.get("views", 0),
                        "total_interactions": cp.get("likes", 0) + cp.get("comments", 0),
                        "post_er": round(((cp.get("likes", 0) + cp.get("comments", 0)) / max(1, followers)) * 100.0, 2),
                        "thumbnail_url": "",
                        "post_url": cp.get("post_url", ""),
                        "is_estimated": cp.get("is_estimated", False),
                        "in_date_range": True,
                    })
                    existing_urls.add(cp["post_url"])

        # Sort posts by timestamp (newest first), posts without timestamp at end
        posts.sort(key=lambda x: x.get("timestamp", "") or "", reverse=True)

        # 4. Follower data: Check SQLite database snapshots first, or use Smart Backfill if enabled
        backfill_setting = self.enable_backfill if enable_backfill is None else enable_backfill
        daily_followers, growth_rate_pct, history_source = storage_service.resolve_follower_history(
            platform=platform,
            handle=handle,
            current_followers=followers,
            start_date=start_date,
            end_date=end_date,
            enable_backfill=backfill_setting,
            total_posts=total_posts_lifetime,
            avg_er=avg_er,
        )

        start_followers = daily_followers[0]["followers"] if daily_followers else followers

        return {
            "handle": handle,
            "display_name": display_name,
            "platform": platform,
            "avatar_url": avatar_url,
            "bio": bio,
            "followers": followers,
            "start_followers": start_followers,
            "growth_rate_pct": growth_rate_pct,
            "following": following,
            "total_posts_lifetime": total_posts_lifetime,
            "is_verified": False,
            "historical_followers": daily_followers,
            "posts": posts,
            "data_source": source_tag,
            "has_real_post_metrics": has_real_post_metrics,
            "history_source": history_source,
        }


# Aliases for seamless compatibility across imports
MockDataService = LiveWebScraperService
ScraperService = LiveWebScraperService

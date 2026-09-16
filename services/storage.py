"""
Local SQLite Storage & Historical Tracking Service.
Manages persistent snapshots of account metrics and posts, supports CSV/Excel
import and export, and provides smart backfill estimation for initial benchmarking.
"""

from __future__ import annotations
import datetime
import io
import logging
import os
import random
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

from utils.helpers import clean_handle

logger = logging.getLogger(__name__)

# Default database path inside <project_root>/data/socialiq.db
DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DEFAULT_DB_PATH = os.path.join(DEFAULT_DATA_DIR, "socialiq.db")


class StorageService:
    """
    Manages SQLite database for historical social media metrics,
    snapshots, caching, and data import/export.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._ensure_db_dir()
        self.init_db()

    def _ensure_db_dir(self) -> None:
        """Create parent directory for database if it doesn't exist."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Return a SQLite connection with row factory enabled."""
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Initialize database tables and indexes."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Account Snapshots Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS account_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    handle TEXT NOT NULL,
                    snapshot_date TEXT NOT NULL,
                    followers INTEGER NOT NULL DEFAULT 0,
                    following INTEGER NOT NULL DEFAULT 0,
                    total_posts INTEGER NOT NULL DEFAULT 0,
                    avg_likes REAL DEFAULT 0.0,
                    avg_comments REAL DEFAULT 0.0,
                    avg_er REAL DEFAULT 0.0,
                    source TEXT DEFAULT 'scraper',
                    recorded_at TEXT NOT NULL,
                    UNIQUE(platform, handle, snapshot_date)
                );
            """)

            # Index for fast timeline queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshots_lookup 
                ON account_snapshots(platform, handle, snapshot_date);
            """)

            # Posts Cache Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posts_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    handle TEXT NOT NULL,
                    post_id TEXT NOT NULL,
                    post_url TEXT,
                    timestamp TEXT,
                    caption TEXT,
                    likes INTEGER DEFAULT 0,
                    comments INTEGER DEFAULT 0,
                    shares INTEGER DEFAULT 0,
                    views INTEGER DEFAULT 0,
                    post_type TEXT,
                    is_estimated INTEGER DEFAULT 0,
                    recorded_at TEXT NOT NULL,
                    UNIQUE(platform, handle, post_id)
                );
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_posts_lookup 
                ON posts_cache(platform, handle, timestamp);
            """)

            conn.commit()

    # =========================================================================
    # SNAPSHOT PERSISTENCE
    # =========================================================================

    def save_account_snapshot(
        self,
        platform: str,
        handle: str,
        followers: int,
        following: int = 0,
        total_posts: int = 0,
        avg_likes: float = 0.0,
        avg_comments: float = 0.0,
        avg_er: float = 0.0,
        snapshot_date: Optional[Union[datetime.date, str]] = None,
        source: str = "scraper",
    ) -> bool:
        """
        Save or update a daily snapshot for an account.
        Re-running on the same day updates the existing snapshot.
        """
        cleaned_handle = clean_handle(handle).lower()
        if not cleaned_handle:
            return False

        if snapshot_date is None:
            date_str = datetime.date.today().strftime("%Y-%m-%d")
        elif isinstance(snapshot_date, (datetime.date, datetime.datetime)):
            date_str = snapshot_date.strftime("%Y-%m-%d")
        else:
            date_str = str(snapshot_date)[:10]

        now_iso = datetime.datetime.now().isoformat()

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO account_snapshots (
                        platform, handle, snapshot_date, followers, following, 
                        total_posts, avg_likes, avg_comments, avg_er, source, recorded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(platform, handle, snapshot_date) DO UPDATE SET
                        followers = excluded.followers,
                        following = CASE WHEN excluded.following > 0 THEN excluded.following ELSE account_snapshots.following END,
                        total_posts = CASE WHEN excluded.total_posts > 0 THEN excluded.total_posts ELSE account_snapshots.total_posts END,
                        avg_likes = CASE WHEN excluded.avg_likes > 0 THEN excluded.avg_likes ELSE account_snapshots.avg_likes END,
                        avg_comments = CASE WHEN excluded.avg_comments > 0 THEN excluded.avg_comments ELSE account_snapshots.avg_comments END,
                        avg_er = CASE WHEN excluded.avg_er > 0 THEN excluded.avg_er ELSE account_snapshots.avg_er END,
                        source = excluded.source,
                        recorded_at = excluded.recorded_at;
                """, (
                    platform,
                    cleaned_handle,
                    date_str,
                    max(0, int(followers)),
                    max(0, int(following)),
                    max(0, int(total_posts)),
                    float(avg_likes),
                    float(avg_comments),
                    float(avg_er),
                    source,
                    now_iso,
                ))
                conn.commit()
            return True
        except Exception as e:
            logger.error("Failed to save account snapshot for @%s: %s", cleaned_handle, e)
            return False

    def save_posts_cache(
        self,
        platform: str,
        handle: str,
        posts: List[Dict[str, Any]],
    ) -> int:
        """Save a batch of posts to the cache, ignoring duplicates."""
        cleaned_handle = clean_handle(handle).lower()
        if not cleaned_handle or not posts:
            return 0

        now_iso = datetime.datetime.now().isoformat()
        saved_count = 0

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                for p in posts:
                    post_id = p.get("post_id") or p.get("shortcode") or p.get("post_url", "")
                    if not post_id:
                        continue
                    
                    cursor.execute("""
                        INSERT INTO posts_cache (
                            platform, handle, post_id, post_url, timestamp, caption,
                            likes, comments, shares, views, post_type, is_estimated, recorded_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(platform, handle, post_id) DO UPDATE SET
                            likes = excluded.likes,
                            comments = excluded.comments,
                            shares = excluded.shares,
                            views = excluded.views,
                            recorded_at = excluded.recorded_at;
                    """, (
                        platform,
                        cleaned_handle,
                        str(post_id),
                        p.get("post_url", ""),
                        p.get("timestamp", ""),
                        p.get("caption", ""),
                        int(p.get("likes", 0)),
                        int(p.get("comments", 0)),
                        int(p.get("shares", 0)),
                        int(p.get("views", 0)),
                        p.get("content_type") or p.get("post_type", "Image"),
                        1 if p.get("is_estimated") else 0,
                        now_iso,
                    ))
                    saved_count += 1
                conn.commit()
            return saved_count
        except Exception as e:
            logger.error("Failed to save posts cache for @%s: %s", cleaned_handle, e)
            return 0

    # =========================================================================
    # QUERYING HISTORY
    # =========================================================================

    def get_account_snapshots(
        self,
        platform: str,
        handle: str,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None,
    ) -> List[Dict[str, Any]]:
        """Query recorded snapshots for an account ordered chronologically."""
        cleaned_handle = clean_handle(handle).lower()
        query = """
            SELECT platform, handle, snapshot_date, followers, following, total_posts, 
                   avg_likes, avg_comments, avg_er, source, recorded_at
            FROM account_snapshots
            WHERE handle = ?
        """
        params: List[Any] = [cleaned_handle]

        if platform:
            query += " AND LOWER(platform) = LOWER(?)"
            params.append(platform)

        if start_date:
            query += " AND snapshot_date >= ?"
            params.append(start_date.strftime("%Y-%m-%d"))

        if end_date:
            query += " AND snapshot_date <= ?"
            params.append(end_date.strftime("%Y-%m-%d"))

        query += " ORDER BY snapshot_date ASC"

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error("Failed to fetch snapshots for @%s: %s", cleaned_handle, e)
            return []

    def get_cached_posts(
        self,
        platform: str,
        handle: str,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve cached posts for an account."""
        cleaned_handle = clean_handle(handle).lower()
        query = """
            SELECT platform, handle, post_id, post_url, timestamp, caption,
                   likes, comments, shares, views, post_type, is_estimated
            FROM posts_cache
            WHERE handle = ?
        """
        params: List[Any] = [cleaned_handle]

        if platform:
            query += " AND LOWER(platform) = LOWER(?)"
            params.append(platform)

        if start_date:
            query += " AND substr(timestamp, 1, 10) >= ?"
            params.append(start_date.strftime("%Y-%m-%d"))

        if end_date:
            query += " AND substr(timestamp, 1, 10) <= ?"
            params.append(end_date.strftime("%Y-%m-%d"))

        query += " ORDER BY timestamp DESC"

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                result = []
                for r in rows:
                    item = dict(r)
                    item["is_estimated"] = bool(item.get("is_estimated", 0))
                    result.append(item)
                return result
        except Exception as e:
            logger.error("Failed to fetch cached posts for @%s: %s", cleaned_handle, e)
            return []

    # =========================================================================
    # HISTORICAL TRAJECTORY RESOLVER & SMART BACKFILL
    # =========================================================================

    def resolve_follower_history(
        self,
        platform: str,
        handle: str,
        current_followers: int,
        start_date: datetime.date,
        end_date: datetime.date,
        enable_backfill: bool = True,
        total_posts: int = 0,
        avg_er: float = 0.0,
    ) -> Tuple[List[Dict[str, Any]], float, str]:
        """
        Resolves daily follower counts for the requested period.
        Priority:
        1. If database has >= 2 snapshot points across the date range, use real historical records.
        2. If database has 1 point or is missing and enable_backfill is True,
           generate realistic smart backfill trajectory.
        3. Otherwise, return flat line at current follower count (0% growth).

        Returns:
            (daily_followers_list, growth_rate_pct, history_source)
            history_source: 'database' | 'smart_backfill' | 'flat'
        """
        cleaned_handle = clean_handle(handle).lower()
        days_count = max(1, (end_date - start_date).days + 1)
        
        # 1. Check existing snapshots in database
        snapshots = self.get_account_snapshots(
            platform=platform,
            handle=cleaned_handle,
            start_date=start_date,
            end_date=end_date,
        )

        # Build map of existing date -> followers
        known_dates: Dict[str, int] = {s["snapshot_date"]: s["followers"] for s in snapshots if s["followers"] > 0}
        
        # Include current snapshot today if available
        today_str = end_date.strftime("%Y-%m-%d")
        if current_followers > 0 and today_str not in known_dates:
            known_dates[today_str] = current_followers

        # Check if we have at least 2 distinct date points with actual variation or span
        if len(known_dates) >= 2:
            sorted_dates = sorted(known_dates.keys())
            
            # Linearly interpolate missing intermediate days
            daily_series: List[Dict[str, Any]] = []
            date_range_idx = pd.date_range(start=start_date, end=end_date, freq="D")
            series_data = {pd.to_datetime(d): known_dates.get(d.strftime("%Y-%m-%d"), None) for d in date_range_idx}
            s = pd.Series(series_data)
            
            # Forward and backward fill, then interpolate
            s = s.interpolate(method="time").bfill().ffill()

            for ts, val in s.items():
                daily_series.append({
                    "date": ts.strftime("%Y-%m-%d"),
                    "followers": int(round(val)),
                })

            start_val = daily_series[0]["followers"]
            end_val = daily_series[-1]["followers"]
            growth_pct = round(((end_val - start_val) / max(1, start_val)) * 100.0, 2)
            
            return daily_series, growth_pct, "database"

        # 2. Smart Backfill when insufficient snapshots exist
        if enable_backfill and current_followers > 0 and days_count > 1:
            backfilled_series, growth_pct = self.generate_smart_backfill(
                handle=cleaned_handle,
                current_followers=current_followers,
                start_date=start_date,
                end_date=end_date,
                total_posts=total_posts,
                avg_er=avg_er,
            )
            return backfilled_series, growth_pct, "smart_backfill"

        # 3. Flat Line Fallback
        daily_series = []
        for i in range(min(days_count, 90)):
            d = start_date + datetime.timedelta(days=i)
            daily_series.append({
                "date": d.strftime("%Y-%m-%d"),
                "followers": current_followers,
            })
        return daily_series, 0.0, "flat"

    def generate_smart_backfill(
        self,
        handle: str,
        current_followers: int,
        start_date: datetime.date,
        end_date: datetime.date,
        total_posts: int = 0,
        avg_er: float = 0.0,
    ) -> Tuple[List[Dict[str, Any]], float]:
        """
        Generates realistic, organic follower growth trajectory back in time.
        - Deterministic using handle hash (reproducible for the same account).
        - Models organic social media dynamics (typical monthly growth 0.8% - 2.8%).
        - Ends exactly at current_followers on end_date.
        """
        days_count = max(1, (end_date - start_date).days + 1)
        if current_followers <= 0:
            return [{"date": (start_date + datetime.timedelta(days=i)).strftime("%Y-%m-%d"), "followers": 0} for i in range(days_count)], 0.0

        # Deterministic seed from handle string
        seed_val = int(sum(ord(c) for c in handle)) + 42
        rng = random.Random(seed_val)

        # Base 30-day organic growth rate between 0.8% and 2.4%
        base_30d_growth = 0.8 + (rng.random() * 1.6)
        
        # Boost slightly if account has higher ER or active posts
        if avg_er > 3.0:
            base_30d_growth += 0.5
        if total_posts > 500:
            base_30d_growth += 0.2

        # Scale to total period duration (e.g., 14 days, 30 days, 60 days)
        period_ratio = days_count / 30.0
        total_growth_pct = round(base_30d_growth * period_ratio, 2)
        total_growth_pct = max(0.2, min(8.0, total_growth_pct))  # Bound between 0.2% and 8.0%

        start_followers = int(round(current_followers / (1.0 + (total_growth_pct / 100.0))))
        total_gain = current_followers - start_followers

        # Generate incremental steps with slight daily fluctuations
        weights = []
        for i in range(days_count):
            day_obj = start_date + datetime.timedelta(days=i)
            # Weekend posts typically have slightly different growth pulses
            weekday = day_obj.weekday()
            pulse = 1.2 if weekday in [4, 5, 6] else 0.9
            noise = 0.7 + (rng.random() * 0.6)
            weights.append(pulse * noise)

        sum_weights = sum(weights) or 1.0
        daily_series = []
        accumulated_gain = 0.0

        for i in range(days_count):
            d = start_date + datetime.timedelta(days=i)
            if i == days_count - 1:
                # Force last day to be exactly current_followers
                followers_at_day = current_followers
            else:
                step_gain = (weights[i] / sum_weights) * total_gain
                accumulated_gain += step_gain
                followers_at_day = int(round(start_followers + accumulated_gain))
                # Ensure monotonicity
                followers_at_day = max(start_followers, min(current_followers, followers_at_day))

            daily_series.append({
                "date": d.strftime("%Y-%m-%d"),
                "followers": followers_at_day,
            })

        calculated_growth = round(((current_followers - start_followers) / max(1, start_followers)) * 100.0, 2)
        return daily_series, calculated_growth

    # =========================================================================
    # IMPORT & EXPORT
    # =========================================================================

    def import_history_file(
        self,
        file_obj: Union[io.BytesIO, bytes],
        filename: str,
    ) -> Tuple[bool, str, int]:
        """
        Imports historical snapshots from CSV or Excel file.
        Accepts flexible column headers in Indonesian and English:
        - date: 'date', 'tanggal', 'tgl', 'snapshot_date'
        - handle: 'handle', 'username', 'akun', 'account'
        - platform: 'platform' (default: 'Instagram' if missing)
        - followers: 'followers', 'follower', 'pengikut'
        - following: 'following', 'mengikuti'
        - total_posts: 'total_posts', 'posts', 'post'
        - avg_er: 'avg_er', 'er', 'er_pct'
        """
        try:
            if isinstance(file_obj, bytes):
                file_buffer = io.BytesIO(file_obj)
            else:
                file_buffer = file_obj

            lower_filename = filename.lower()
            if lower_filename.endswith((".xlsx", ".xls")):
                df = pd.read_excel(file_buffer)
            else:
                df = pd.read_csv(file_buffer)

            if df.empty:
                return False, "File kosong, tidak ada baris data.", 0

            # Normalize column names: lowercase, strip spaces, replace underscores
            col_map = {}
            for col in df.columns:
                c_norm = str(col).strip().lower().replace(" ", "_")
                if c_norm in ["date", "tanggal", "tgl", "snapshot_date", "waktu"]:
                    col_map["date"] = col
                elif c_norm in ["handle", "username", "akun", "account", "user", "profil"]:
                    col_map["handle"] = col
                elif c_norm in ["platform", "sosmed", "media"]:
                    col_map["platform"] = col
                elif c_norm in ["followers", "follower", "pengikut", "subs"]:
                    col_map["followers"] = col
                elif c_norm in ["following", "mengikuti"]:
                    col_map["following"] = col
                elif c_norm in ["total_posts", "posts", "post", "postingan"]:
                    col_map["total_posts"] = col
                elif c_norm in ["avg_er", "er", "er_pct", "engagement_rate"]:
                    col_map["avg_er"] = col

            if "date" not in col_map or "handle" not in col_map or "followers" not in col_map:
                return (
                    False,
                    "Kolom wajib tidak ditemukan! File harus memiliki kolom: 'date' (tanggal), 'handle' (username), dan 'followers'.",
                    0,
                )

            imported_count = 0
            for _, row in df.iterrows():
                raw_handle = str(row[col_map["handle"]]).strip()
                cleaned_handle = clean_handle(raw_handle)
                if not cleaned_handle or cleaned_handle == "nan":
                    continue

                raw_date = row[col_map["date"]]
                try:
                    parsed_date = pd.to_datetime(raw_date).strftime("%Y-%m-%d")
                except Exception:
                    continue

                try:
                    followers_val = int(float(row[col_map["followers"]]))
                except (ValueError, TypeError):
                    followers_val = 0

                platform_val = "Instagram"
                if "platform" in col_map and pd.notna(row[col_map["platform"]]):
                    platform_val = str(row[col_map["platform"]]).strip().capitalize()

                following_val = 0
                if "following" in col_map and pd.notna(row[col_map["following"]]):
                    try:
                        following_val = int(float(row[col_map["following"]]))
                    except (ValueError, TypeError):
                        pass

                total_posts_val = 0
                if "total_posts" in col_map and pd.notna(row[col_map["total_posts"]]):
                    try:
                        total_posts_val = int(float(row[col_map["total_posts"]]))
                    except (ValueError, TypeError):
                        pass

                avg_er_val = 0.0
                if "avg_er" in col_map and pd.notna(row[col_map["avg_er"]]):
                    try:
                        avg_er_val = float(str(row[col_map["avg_er"]]).replace("%", ""))
                    except (ValueError, TypeError):
                        pass

                saved = self.save_account_snapshot(
                    platform=platform_val,
                    handle=cleaned_handle,
                    followers=followers_val,
                    following=following_val,
                    total_posts=total_posts_val,
                    avg_er=avg_er_val,
                    snapshot_date=parsed_date,
                    source="imported",
                )
                if saved:
                    imported_count += 1

            return (
                True,
                f"Sukses mengimpor {imported_count} baris data snapshot historis.",
                imported_count,
            )
        except Exception as e:
            logger.error("Error importing file %s: %s", filename, e, exc_info=True)
            return False, f"Terjadi kesalahan saat memproses file: {str(e)}", 0

    def export_history_df(self, handles: Optional[List[str]] = None) -> pd.DataFrame:
        """Export stored snapshots as a clean pandas DataFrame."""
        query = """
            SELECT platform, handle, snapshot_date as date, followers, following, 
                   total_posts, avg_er as er_pct, source, recorded_at
            FROM account_snapshots
        """
        params: List[Any] = []
        if handles:
            clean_handles = [clean_handle(h).lower() for h in handles if clean_handle(h)]
            if clean_handles:
                placeholders = ",".join("?" for _ in clean_handles)
                query += f" WHERE handle IN ({placeholders})"
                params.extend(clean_handles)

        query += " ORDER BY handle ASC, snapshot_date ASC"

        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)

    def get_sample_template_bytes(self, file_format: str = "xlsx") -> bytes:
        """Generate a ready-to-use sample template for historical data import."""
        today = datetime.date.today()
        sample_rows = []
        
        sample_profiles = [
            ("shopee_id", 10_250_000, 4800, 2.1),
            ("tokopedia", 4_800_000, 3900, 1.8),
            ("bliblidotcom", 2_100_000, 3200, 1.5),
        ]

        for handle, base_f, posts, er in sample_profiles:
            for i in range(14, -1, -1):
                d = today - datetime.timedelta(days=i)
                f_growth = base_f + int((14 - i) * (base_f * 0.0006))
                sample_rows.append({
                    "date": d.strftime("%Y-%m-%d"),
                    "platform": "Instagram",
                    "handle": handle,
                    "followers": f_growth,
                    "following": 120,
                    "total_posts": posts + int((14 - i) * 0.8),
                    "avg_er": er,
                })

        df = pd.DataFrame(sample_rows)
        output = io.BytesIO()

        if file_format.lower() == "csv":
            df.to_csv(output, index=False)
            return output.getvalue()
        else:
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Historical_Data")
            return output.getvalue()


# Global storage singleton
storage_service = StorageService()

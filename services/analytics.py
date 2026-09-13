"""
Analytics and mathematical calculations for social media benchmarking.
Computes KPIs, Engagement Rate (ER), Page Performance Index (PPI),
Timing matrices, and Content Intelligence.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


DAY_NAMES_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def calculate_ppi(avg_er: float, growth_rate_pct: float) -> float:
    """
    Calculate Page Performance Index (PPI) from 0 to 100.
    Combines normalized engagement rate (60% weight) and follower growth (40% weight).
    """
    # Engagement score: 0% ER -> 0, 2.0% ER -> 50, 4.0% ER -> 80, >=5.0% -> 95-100
    er_score = min(100.0, max(0.0, (avg_er / 4.0) * 80.0))
    
    # Growth score: 0% growth -> 50, +3% growth -> 75, +5% growth -> 90
    growth_score = min(100.0, max(0.0, 50.0 + (growth_rate_pct * 8.0)))

    ppi_val = (0.60 * er_score) + (0.40 * growth_score)
    return round(float(np.clip(ppi_val, 5.0, 99.0)), 1)


def calculate_account_kpis(account_data: Dict[str, Any], days_count: int) -> Dict[str, Any]:
    """
    Calculate comprehensive KPIs for a single account over the specified period.
    """
    followers = int(account_data.get("followers", 0))
    growth_rate = float(account_data.get("growth_rate_pct", 0.0))
    posts = account_data.get("posts", [])
    total_posts = len(posts)
    posts_per_day = round(total_posts / max(1, days_count), 2)

    if total_posts == 0 or followers == 0:
        return {
            "handle": account_data.get("handle", ""),
            "display_name": account_data.get("display_name", ""),
            "avatar_url": account_data.get("avatar_url", ""),
            "followers": followers,
            "growth_rate_pct": growth_rate,
            "total_posts": 0,
            "posts_per_day": 0.0,
            "total_likes": 0,
            "avg_likes": 0.0,
            "total_comments": 0,
            "avg_comments": 0.0,
            "total_shares": 0,
            "avg_shares": 0.0,
            "total_saves": 0,
            "avg_saves": 0.0,
            "total_interactions": 0,
            "avg_interactions": 0.0,
            "avg_er": 0.0,
            "avg_er_views": 0.0,
            "ppi": calculate_ppi(0.0, growth_rate),
            "is_main": account_data.get("is_main", False),
        }

    total_likes = sum(p.get("likes", 0) for p in posts)
    total_comments = sum(p.get("comments", 0) for p in posts)
    total_shares = sum(p.get("shares", 0) for p in posts)
    total_saves = sum(p.get("saves", 0) for p in posts)
    total_views = sum(p.get("views", 0) for p in posts)
    total_interactions = total_likes + total_comments + total_shares + total_saves

    avg_likes = total_likes / total_posts
    avg_comments = total_comments / total_posts
    avg_shares = total_shares / total_posts
    avg_saves = total_saves / total_posts
    avg_interactions = total_interactions / total_posts

    # ER by Followers (%)
    avg_er = (avg_interactions / followers) * 100.0
    
    # ER by Views (%)
    avg_er_views = (total_interactions / total_views * 100.0) if total_views > 0 else 0.0

    ppi = calculate_ppi(avg_er, growth_rate)

    return {
        "handle": account_data.get("handle", ""),
        "display_name": account_data.get("display_name", ""),
        "avatar_url": account_data.get("avatar_url", ""),
        "followers": followers,
        "growth_rate_pct": growth_rate,
        "total_posts": total_posts,
        "posts_per_day": posts_per_day,
        "total_likes": total_likes,
        "avg_likes": round(avg_likes, 1),
        "total_comments": total_comments,
        "avg_comments": round(avg_comments, 1),
        "total_shares": total_shares,
        "avg_shares": round(avg_shares, 1),
        "total_saves": total_saves,
        "avg_saves": round(avg_saves, 1),
        "total_interactions": total_interactions,
        "avg_interactions": round(avg_interactions, 1),
        "avg_er": round(avg_er, 2),
        "avg_er_views": round(avg_er_views, 2),
        "ppi": ppi,
        "is_main": account_data.get("is_main", False),
    }


def build_comparison_matrix(all_accounts_data: List[Dict[str, Any]], days_count: int) -> pd.DataFrame:
    """
    Build the main Benchmark Comparison DataFrame across all profiles.
    """
    rows = []
    for acc in all_accounts_data:
        kpi = calculate_account_kpis(acc, days_count)
        rows.append({
            "Profile": f"@{kpi['handle']}" + (" (You)" if kpi["is_main"] else ""),
            "Handle": kpi["handle"],
            "Followers": kpi["followers"],
            "Growth (%)": kpi["growth_rate_pct"],
            "Total Posts": kpi["total_posts"],
            "Posts/Day": kpi["posts_per_day"],
            "Avg Likes": int(round(kpi["avg_likes"])),
            "Avg Comments": int(round(kpi["avg_comments"])),
            "Shares/Saves": int(round(kpi["avg_shares"] + kpi["avg_saves"])),
            "Avg Interactions": int(round(kpi["avg_interactions"])),
            "PPI": kpi["ppi"],
            "ER (%)": kpi["avg_er"],
            "Is Main": kpi["is_main"],
            "Avatar": kpi["avatar_url"],
        })

    df = pd.DataFrame(rows)
    # Sort with Main profile on top or by PPI descending
    return df


def flatten_all_posts(all_accounts_data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Combine all posts from all accounts into a single flat DataFrame.
    Guarantees account, day_of_week, and hour are always populated.
    """
    all_posts = []
    for acc in all_accounts_data:
        is_main = acc.get("is_main", False)
        handle = acc.get("handle", "")
        for p in acc.get("posts", []):
            p_copy = dict(p)
            p_copy["is_main"] = is_main
            if "account" not in p_copy:
                p_copy["account"] = handle

            # Ensure day_of_week, hour, and date exist
            ts = p_copy.get("timestamp")
            dt = None
            if ts:
                try:
                    if isinstance(ts, str):
                        dt = datetime.datetime.fromisoformat(ts)
                    else:
                        dt = ts
                except Exception:
                    dt = None

            if "day_of_week" not in p_copy:
                p_copy["day_of_week"] = dt.weekday() if dt else 0
            if "hour" not in p_copy:
                p_copy["hour"] = dt.hour if dt else 12
            if "date" not in p_copy:
                p_copy["date"] = dt.strftime("%d %b %Y") if dt else "-"

            all_posts.append(p_copy)
    
    if not all_posts:
        return pd.DataFrame()
    return pd.DataFrame(all_posts)


def generate_timing_heatmap_matrix(
    posts_df: pd.DataFrame,
    target_account: Optional[str] = None,
    metric: str = "interactions",
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Generate a 7 Days (Senin-Minggu) x 24 Hours (00-23) matrix for timing analysis.
    Returns the matrix DataFrame and details about the peak best time.
    """
    hours = list(range(24))
    grid = pd.DataFrame(0.0, index=DAY_NAMES_ID, columns=hours)

    if posts_df.empty:
        return grid, {"day": "Senin", "hour": 12, "value": 0.0}

    filtered_df = posts_df.copy()
    if target_account and target_account != "All Accounts" and "account" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["account"] == target_account]

    if filtered_df.empty:
        return grid, {"day": "Senin", "hour": 12, "value": 0.0}

    # Ensure day_of_week and hour columns exist defensively
    if "day_of_week" not in filtered_df.columns or "hour" not in filtered_df.columns:
        if "timestamp" in filtered_df.columns:
            ts_series = pd.to_datetime(filtered_df["timestamp"], errors="coerce")
            filtered_df["day_of_week"] = ts_series.dt.weekday.fillna(0).astype(int)
            filtered_df["hour"] = ts_series.dt.hour.fillna(12).astype(int)
        else:
            filtered_df["day_of_week"] = 0
            filtered_df["hour"] = 12

    # Map day_of_week (0=Monday) to Indonesian day name
    filtered_df["day_name_id"] = filtered_df["day_of_week"].apply(
        lambda x: DAY_NAMES_ID[int(x)] if 0 <= int(x) < 7 else "Senin"
    )

    if metric == "post_count":
        grouped = filtered_df.groupby(["day_name_id", "hour"]).size().reset_index(name="val")
    else:
        # Default: average interactions per post in that slot
        grouped = (
            filtered_df.groupby(["day_name_id", "hour"])["total_interactions"]
            .mean()
            .reset_index(name="val")
        )

    for _, row in grouped.iterrows():
        d_name = row["day_name_id"]
        hr = int(row["hour"])
        val = float(row["val"])
        if d_name in grid.index and hr in grid.columns:
            grid.loc[d_name, hr] = round(val, 1)

    # Find peak best slot
    max_val = grid.values.max()
    peak_day = "Rabu"
    peak_hour = 19
    if max_val > 0:
        for d in DAY_NAMES_ID:
            for h in hours:
                if grid.loc[d, h] == max_val:
                    peak_day = d
                    peak_hour = h
                    break

    peak_info = {
        "day": peak_day,
        "hour": peak_hour,
        "value": float(max_val),
        "hour_label": f"{peak_hour:02d}:00 - {(peak_hour+1)%24:02d}:00",
    }
    return grid, peak_info


def analyze_content_formats(posts_df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze performance grouped by content format (Reels/Video, Carousel, Single Image).
    """
    if posts_df.empty or "content_type" not in posts_df.columns:
        return pd.DataFrame()

    agg_df = (
        posts_df.groupby("content_type")
        .agg(
            total_posts=("post_id", "count"),
            avg_interactions=("total_interactions", "mean"),
            avg_likes=("likes", "mean"),
            avg_comments=("comments", "mean"),
            avg_shares=("shares", "mean"),
            avg_er=("post_er", "mean"),
        )
        .reset_index()
    )

    agg_df["avg_interactions"] = agg_df["avg_interactions"].round(1)
    agg_df["avg_likes"] = agg_df["avg_likes"].round(1)
    agg_df["avg_comments"] = agg_df["avg_comments"].round(1)
    agg_df["avg_shares"] = agg_df["avg_shares"].round(1)
    agg_df["avg_er"] = agg_df["avg_er"].round(2)
    agg_df = agg_df.sort_values(by="avg_interactions", ascending=False)
    return agg_df


def extract_top_hashtags(posts_df: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    """
    Extract hashtags from posts and calculate frequency, total interactions, and average ER.
    """
    if posts_df.empty:
        return pd.DataFrame()

    tag_rows = []
    for _, row in posts_df.iterrows():
        tags = row.get("hashtags", [])
        if not tags and isinstance(row.get("caption"), str):
            tags = re.findall(r"#\w+", row["caption"])
        
        interactions = row.get("total_interactions", 0)
        post_er = row.get("post_er", 0.0)

        for tag in tags:
            tag_clean = tag.strip()
            if tag_clean:
                tag_rows.append({
                    "hashtag": tag_clean,
                    "interactions": interactions,
                    "post_er": post_er,
                })

    if not tag_rows:
        return pd.DataFrame()

    tag_df = pd.DataFrame(tag_rows)
    summary = (
        tag_df.groupby("hashtag")
        .agg(
            count=("interactions", "count"),
            total_interactions=("interactions", "sum"),
            avg_interactions=("interactions", "mean"),
            avg_er=("post_er", "mean"),
        )
        .reset_index()
    )

    summary["avg_interactions"] = summary["avg_interactions"].round(1)
    summary["avg_er"] = summary["avg_er"].round(2)
    summary = summary.sort_values(by="avg_interactions", ascending=False).head(top_n)
    return summary

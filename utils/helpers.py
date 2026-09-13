"""
Helper utilities for parsing, formatting, and data export.
"""

from __future__ import annotations
import io
import re
from urllib.parse import urlparse
import pandas as pd


def clean_handle(input_str: str) -> str:
    """
    Extract clean username/handle from URLs or raw input strings.
    Examples:
        'https://instagram.com/starbucks/?hl=en' -> 'starbucks'
        'https://www.tiktok.com/@apple' -> 'apple'
        'https://threads.net/@nike' -> 'nike'
        '@mybrand' -> 'mybrand'
        '  mybrand  ' -> 'mybrand'
    """
    if not input_str:
        return ""
    
    val = input_str.strip()
    
    # Check if input is a URL
    if val.startswith("http://") or val.startswith("https://"):
        try:
            parsed = urlparse(val)
            path_segments = [seg for seg in parsed.path.strip("/").split("/") if seg]
            if path_segments:
                # Handle URLs like tiktok.com/@username
                raw_handle = path_segments[0]
                if raw_handle.startswith("@"):
                    return raw_handle.lstrip("@").strip()
                # For some URLs like instagram.com/p/... or user profile
                return raw_handle.strip()
        except Exception:
            pass

    # Remove URL parameters if any remain
    val = val.split("?")[0].split("#")[0]
    # Remove leading '@' or slashes
    val = val.strip().lstrip("@").strip("/")
    # Sanitize characters: keep alphanumeric, dot, and underscore
    clean = re.sub(r"[^a-zA-Z0-9._]", "", val)
    return clean


def format_number(num: float | int | None) -> str:
    """
    Format large numbers into human-readable strings (e.g. 1.25M, 45.3K).
    """
    if num is None or pd.isna(num):
        return "0"
    
    try:
        val = float(num)
    except (ValueError, TypeError):
        return str(num)

    abs_val = abs(val)
    sign = "-" if val < 0 else ""

    if abs_val >= 1_000_000_000:
        return f"{sign}{abs_val / 1_000_000_000:.2f}B"
    if abs_val >= 1_000_000:
        return f"{sign}{abs_val / 1_000_000:.2f}M"
    if abs_val >= 1_000:
        return f"{sign}{abs_val / 1_000:.1f}K"
    if abs_val >= 10:
        return f"{sign}{abs_val:.0f}"
    return f"{sign}{abs_val:.1f}" if abs_val % 1 != 0 else f"{sign}{int(abs_val)}"


def format_percent(val: float | int | None, precision: int = 2) -> str:
    """
    Format float percentage into formatted string (e.g. 3.45%).
    """
    if val is None or pd.isna(val):
        return "0.00%"
    try:
        return f"{float(val):.{precision}f}%"
    except (ValueError, TypeError):
        return "0.00%"


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    """
    Convert pandas DataFrame to UTF-8 CSV bytes for download.
    """
    return df.to_csv(index=False).encode("utf-8")


def to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Benchmark") -> bytes:
    """
    Convert pandas DataFrame to Excel (.xlsx) bytes for download.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output.getvalue()

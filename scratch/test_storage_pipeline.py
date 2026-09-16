"""
Verification test for SocialIQ historical tracking, storage service,
CSV/Excel import & export, smart backfill, and end-to-end benchmarking.
"""

from __future__ import annotations
import datetime
import io
import os
import sys
import pandas as pd

# Add workspace root to sys.path
sys.path.insert(0, os.path.abspath("."))

from services.storage import StorageService
from services.data_fetcher import LiveWebScraperService
from services.analytics import calculate_account_kpis, build_comparison_matrix
from components.charts import create_follower_growth_chart


def run_all_tests():
    print("=== Test 1: SQLite Storage Service & Tables Initialization ===")
    test_db_path = os.path.abspath("scratch/test_socialiq.db")
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    storage = StorageService(db_path=test_db_path)
    assert os.path.exists(test_db_path), "Database file was not created!"
    print("✓ Test database initialized successfully at:", test_db_path)

    print("\n=== Test 2: Snapshot Persistence & Querying ===")
    today = datetime.date.today()
    d1 = today - datetime.timedelta(days=5)
    d2 = today

    ok1 = storage.save_account_snapshot(
        platform="Instagram",
        handle="testbrand",
        followers=100_000,
        following=250,
        total_posts=500,
        avg_er=2.4,
        snapshot_date=d1,
    )
    ok2 = storage.save_account_snapshot(
        platform="Instagram",
        handle="testbrand",
        followers=102_500,
        following=255,
        total_posts=508,
        avg_er=2.6,
        snapshot_date=d2,
    )
    assert ok1 and ok2, "Failed to save snapshots!"

    history = storage.get_account_snapshots("Instagram", "testbrand")
    assert len(history) == 2, f"Expected 2 snapshots, found {len(history)}"
    assert history[0]["followers"] == 100_000
    assert history[1]["followers"] == 102_500
    print(f"✓ Snapshots verified. History records: {len(history)}")

    print("\n=== Test 3: History Resolver (With Existing DB Data) ===")
    series, growth_pct, source = storage.resolve_follower_history(
        platform="Instagram",
        handle="testbrand",
        current_followers=102_500,
        start_date=d1,
        end_date=d2,
        enable_backfill=True,
    )
    assert source == "database", f"Expected 'database', got {source}"
    assert len(series) == 6, f"Expected 6 days, got {len(series)}"
    assert series[0]["followers"] == 100_000
    assert series[-1]["followers"] == 102_500
    assert growth_pct == 2.5, f"Expected 2.5% growth, got {growth_pct}%"
    print(f"✓ DB History resolved. Growth: {growth_pct}%, Days: {len(series)}")

    print("\n=== Test 4: Smart Backfill (For New Account Without DB History) ===")
    start_30d = today - datetime.timedelta(days=29)
    bf_series, bf_growth, bf_source = storage.resolve_follower_history(
        platform="Instagram",
        handle="new_brand_without_history",
        current_followers=50_000,
        start_date=start_30d,
        end_date=today,
        enable_backfill=True,
        total_posts=200,
        avg_er=3.2,
    )
    assert bf_source == "smart_backfill", f"Expected 'smart_backfill', got {bf_source}"
    assert len(bf_series) == 30, f"Expected 30 days, got {len(bf_series)}"
    assert bf_series[-1]["followers"] == 50_000, "End follower count must match current followers exactly!"
    assert bf_growth > 0.0, f"Expected positive growth rate, got {bf_growth}%"
    assert bf_series[0]["followers"] < 50_000, "Start follower count must be lower than end"
    print(f"✓ Smart Backfill verified. Estimated 30-day Growth: {bf_growth}%, Start: {bf_series[0]['followers']} -> End: {bf_series[-1]['followers']}")

    print("\n=== Test 5: Template Generation & CSV/Excel Import ===")
    tpl_bytes = storage.get_sample_template_bytes(file_format="xlsx")
    assert len(tpl_bytes) > 0, "Template bytes empty!"
    df_tpl = pd.read_excel(io.BytesIO(tpl_bytes))
    assert not df_tpl.empty, "Template DataFrame empty!"
    assert "handle" in df_tpl.columns and "followers" in df_tpl.columns and "date" in df_tpl.columns
    print(f"✓ Excel Template generated successfully ({len(df_tpl)} rows).")

    # Import template into database
    import_ok, import_msg, count = storage.import_history_file(tpl_bytes, "template.xlsx")
    assert import_ok, f"Import failed: {import_msg}"
    assert count > 0, "Imported count should be > 0"
    print(f"✓ Import verified: {import_msg} (Imported: {count} rows)")

    # Verify imported handles are now present in SQLite
    export_df = storage.export_history_df()
    assert not export_df.empty, "Export DF empty after import!"
    handles_found = export_df["handle"].unique()
    assert "shopee_id" in handles_found and "tokopedia" in handles_found
    print(f"✓ Export verified. Stored accounts: {list(handles_found)}")

    print("\n=== Test 6: End-to-End Analytics & Chart Generation ===")
    scraper = LiveWebScraperService(enable_backfill=True)
    # Test single account data structure
    start_dt = today - datetime.timedelta(days=14)
    res = scraper.fetch_account_data("Instagram", "testbrand", start_dt, today)
    assert "historical_followers" in res
    assert "history_source" in res
    assert len(res["historical_followers"]) == 15

    # Check chart generation doesn't throw
    fig = create_follower_growth_chart([res])
    assert fig is not None
    print(f"✓ Follower Growth Chart generated successfully with {len(fig.data)} traces.")

    # Cleanup test db
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_all_tests()

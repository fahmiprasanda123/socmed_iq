"""
Automated unit and integration test for social media benchmarking dashboard.
Tests data fetcher, analytics formulas, and Plotly visualization generation.
"""

import datetime
import os
import sys

# Ensure current directory is on pythonpath
sys.path.insert(0, os.path.abspath("."))

from utils.helpers import clean_handle, format_number, format_percent, to_csv_bytes, to_excel_bytes
from services.data_fetcher import MockDataService, ScraperService
from services.analytics import (
    calculate_account_kpis,
    build_comparison_matrix,
    flatten_all_posts,
    generate_timing_heatmap_matrix,
    analyze_content_formats,
    extract_top_hashtags,
)
from components.charts import (
    create_quadrant_scatter,
    create_timing_heatmap,
    create_format_performance_bar,
    create_hashtag_bar,
    create_follower_growth_chart,
)


def run_tests():
    print("=== 1. Testing Utils & Helpers ===")
    assert clean_handle("https://www.instagram.com/mybrand/?hl=en") == "mybrand", f"Failed handle URL parsing"
    assert clean_handle("@mybrand") == "mybrand", f"Failed handle @ parsing"
    assert clean_handle("https://tiktok.com/@creator") == "creator", f"Failed TikTok URL parsing"
    assert format_number(1_250_000) == "1.25M"
    assert format_number(45_300) == "45.3K"
    assert format_percent(3.456) == "3.46%"
    print("✓ Helpers passed!")

    print("=== 2. Testing Data Fetcher Services ===")
    mock_service = MockDataService()
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=14)

    # Benchmark dataset
    dataset = mock_service.fetch_benchmark_dataset(
        platform="Instagram",
        main_account="shopee_id",
        competitors=["tokopedia", "bliblidotcom", "lazada_id"],
        start_date=start_date,
        end_date=today,
    )

    assert len(dataset["accounts"]) == 4, f"Expected 4 accounts, got {len(dataset['accounts'])}"
    main_acc = next(a for a in dataset["accounts"] if a["is_main"])
    assert main_acc["handle"] == "shopee_id"
    assert len(main_acc["posts"]) > 0
    assert len(main_acc["historical_followers"]) == 15
    print(f"✓ MockDataService passed (fetched {len(dataset['accounts'])} accounts with posts and followers)")

    # Test ScraperService fallback
    scraper_service = ScraperService(api_token=None)
    scraper_res = scraper_service.fetch_account_data("Instagram", "nike", start_date, today)
    assert scraper_res["handle"] == "nike"
    assert "Fallback" in scraper_res["data_source"]
    print("✓ ScraperService fallback architecture verified!")

    print("=== 3. Testing Analytics Engine ===")
    accounts = dataset["accounts"]
    days_count = dataset["date_range"]["days"]

    # Matrix
    comparison_df = build_comparison_matrix(accounts, days_count)
    assert not comparison_df.empty
    assert "PPI" in comparison_df.columns
    assert "ER (%)" in comparison_df.columns
    assert "Posts/Day" in comparison_df.columns
    print(f"✓ Comparison matrix calculated:\n{comparison_df[['Profile', 'Followers', 'ER (%)', 'PPI', 'Posts/Day']]}")

    # Posts flattening
    posts_df = flatten_all_posts(accounts)
    assert not posts_df.empty
    print(f"✓ Total posts analyzed: {len(posts_df)}")

    # Timing Heatmap
    heatmap_matrix, peak_info = generate_timing_heatmap_matrix(posts_df, target_account="All Accounts")
    assert heatmap_matrix.shape == (7, 24)
    assert peak_info["day"] in ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    print(f"✓ Timing heatmap generated. Optimal slot: {peak_info['day']} at {peak_info['hour_label']} ({peak_info['value']} avg interactions)")

    # Format Performance
    format_df = analyze_content_formats(posts_df)
    assert not format_df.empty
    print(f"✓ Content formats evaluated: {format_df['content_type'].tolist()}")

    # Hashtags
    hashtag_df = extract_top_hashtags(posts_df, top_n=10)
    assert not hashtag_df.empty
    print(f"✓ Top hashtags detected: {len(hashtag_df)} tags (Top: {hashtag_df.iloc[0]['hashtag']})")

    print("=== 4. Testing Plotly Charts Generation ===")
    fig_scatter = create_quadrant_scatter(comparison_df, "shopee_id")
    assert fig_scatter is not None
    
    fig_heatmap = create_timing_heatmap(heatmap_matrix, peak_info)
    assert fig_heatmap is not None

    fig_format = create_format_performance_bar(format_df)
    assert fig_format is not None

    fig_hashtag = create_hashtag_bar(hashtag_df)
    assert fig_hashtag is not None

    fig_growth = create_follower_growth_chart(accounts)
    assert fig_growth is not None
    print("✓ All Plotly figures generated successfully without errors!")

    print("=== 5. Testing Export Bytes ===")
    csv_bytes = to_csv_bytes(comparison_df)
    assert len(csv_bytes) > 0
    xlsx_bytes = to_excel_bytes(comparison_df)
    assert len(xlsx_bytes) > 0
    print("✓ CSV and Excel export bytes verified successfully!")

    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_tests()

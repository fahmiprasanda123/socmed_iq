"""
Test suite for SocialIQ Growth & Viral Suite:
1. Helpers: format_idr
2. Commercial Rate Card & Sponsorship Estimator
3. Audience Health & Ghost Follower Audit
4. AI "Steal Like an Artist" Content Strategist
5. Account Battle Card (PNG Infographic Generator)
6. One-Click Executive Client Audit Deck (HTML / Print PDF)
"""

from __future__ import annotations
import os
import sys
import pandas as pd

# Add workspace root to sys.path
sys.path.insert(0, os.path.abspath("."))

from utils.helpers import format_idr
from services.analytics import (
    calculate_rate_card_and_commercial_value,
    audit_audience_health,
    generate_counter_content_strategies,
    generate_executive_audit_html,
)
from components.charts import generate_battle_card_image


def test_growth_features():
    print("=== Test 1: format_idr ===")
    assert format_idr(0) == "Rp 0"
    assert format_idr(450_000) == "Rp 450 Rb"
    assert "Jt" in format_idr(1_500_000)
    assert "Miliar" in format_idr(2_500_000_000)
    print("✓ format_idr passed!")

    print("\n=== Test 2: Commercial Rate Card Estimator ===")
    # Nano creator with high ER
    nano_kpis = {
        "followers": 8_500,
        "avg_er": 5.2,
        "avg_interactions": 442,
    }
    nano_rate = calculate_rate_card_and_commercial_value(nano_kpis, platform="Instagram")
    assert nano_rate["tier_code"] == "nano"
    assert nano_rate["feed_min"] > 0
    assert nano_rate["feed_max"] > nano_rate["feed_min"]
    assert nano_rate["reels_max"] > nano_rate["feed_max"]
    assert nano_rate["story_min"] < nano_rate["feed_min"]
    assert "High ROI" in nano_rate["commercial_rating"]
    print(f"✓ Nano Rate Card: Feed {nano_rate['feed_min']:,} - {nano_rate['feed_max']:,} IDR (Rating: {nano_rate['commercial_rating']})")

    # Macro creator with standard ER
    macro_kpis = {
        "followers": 450_000,
        "avg_er": 1.8,
        "avg_interactions": 8_100,
    }
    macro_rate = calculate_rate_card_and_commercial_value(macro_kpis, platform="Instagram")
    assert macro_rate["tier_code"] == "macro"
    assert macro_rate["feed_min"] >= 4_000_000
    print(f"✓ Macro Rate Card: Feed {macro_rate['feed_min']:,} - {macro_rate['feed_max']:,} IDR (Tier: {macro_rate['tier_name']})")

    print("\n=== Test 3: Audience Health & Ghost Follower Audit ===")
    # Healthy organic account
    healthy_kpis = {
        "followers": 25_000,
        "avg_er": 3.8,
        "avg_likes": 900,
        "avg_comments": 50,
        "posts_per_day": 1.0,
    }
    h_res = audit_audience_health(healthy_kpis)
    assert h_res["grade"] in ["A+", "A", "B"]
    assert h_res["health_score"] >= 70
    assert h_res["ghost_risk_pct"] < 35.0
    print(f"✓ Healthy Account: Grade {h_res['grade']}, Score {h_res['health_score']}/100, Ghost Risk: {h_res['ghost_risk_pct']}%")

    # Inactive / ghost follower suspected account
    dead_kpis = {
        "followers": 300_000,
        "avg_er": 0.1,
        "avg_likes": 250,
        "avg_comments": 2,
        "posts_per_day": 0.1,
    }
    d_res = audit_audience_health(dead_kpis)
    assert d_res["grade"] in ["D", "F"]
    assert d_res["ghost_risk_pct"] > 50.0
    print(f"✓ Suspected Ghost Account: Grade {d_res['grade']}, Score {d_res['health_score']}/100, Ghost Risk: {d_res['ghost_risk_pct']}%")

    print("\n=== Test 4: AI 'Steal Like an Artist' Content Strategist ===")
    mock_posts = pd.DataFrame([
        {
            "account": "competitor_coffee",
            "caption": "Jangan pernah beli kopi susu sebelum tahu rahasia beans ini! #kopi #barista",
            "content_type": "Carousel",
            "likes": 5200,
            "comments": 240,
            "post_er": 4.5,
            "total_interactions": 5440,
            "post_url": "https://instagram.com/p/test1",
        },
        {
            "account": "competitor_coffee",
            "caption": "Review jujur 3 menu paling laris bulan ini, mana yang worth it?",
            "content_type": "Reel",
            "likes": 4100,
            "comments": 190,
            "post_er": 3.8,
            "total_interactions": 4290,
            "post_url": "https://instagram.com/p/test2",
        },
    ])
    strategies = generate_counter_content_strategies(mock_posts, main_handle="my_coffee")
    assert len(strategies) > 0
    first_strat = strategies[0]
    assert "competitor_post" in first_strat
    assert "counter_ideas" in first_strat
    assert len(first_strat["counter_ideas"]) == 2 or len(first_strat["counter_ideas"]) == 3
    first_idea = first_strat["counter_ideas"][0]
    assert "hook" in first_idea and len(first_idea["hook"]) > 5
    assert "cta" in first_idea and len(first_idea["cta"]) > 5
    print(f"✓ AI Content Strategist generated {len(strategies)} strategies. Sample hook:\n   '{first_idea['hook']}'")

    print("\n=== Test 5: Account Battle Card (PNG Generation) ===")
    main_kpi = {
        "Profile": "kopikenangan.id",
        "Followers": 750_000,
        "ER (%)": 3.4,
        "PPI": 81.5,
        "Posts/Day": 1.2,
    }
    comp_kpi = {
        "Profile": "fore.coffee",
        "Followers": 620_000,
        "ER (%)": 2.8,
        "PPI": 75.0,
        "Posts/Day": 0.9,
    }
    png_bytes = generate_battle_card_image(main_kpi, comp_kpi, platform="Instagram")
    assert len(png_bytes) > 5_000, "Battle Card PNG bytes too small or empty!"
    # PNG header check
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n"), "Invalid PNG byte header!"
    print(f"✓ Battle Card PNG generated successfully ({len(png_bytes):,} bytes).")

    print("\n=== Test 6: One-Click Executive Client Audit Deck (HTML) ===")
    comp_df = pd.DataFrame([
        {
            "Profile": "kopikenangan.id",
            "Followers": 750_000,
            "Growth (%)": 2.4,
            "Lifetime Posts": 1400,
            "Total Posts": 36,
            "Posts/Day": 1.2,
            "Avg Likes": 25000,
            "Avg Comments": 350,
            "Shares/Saves": 2100,
            "PPI": 81.5,
            "ER (%)": 3.4,
            "Is Main": True,
        },
        {
            "Profile": "fore.coffee",
            "Followers": 620_000,
            "Growth (%)": 1.8,
            "Lifetime Posts": 980,
            "Total Posts": 28,
            "Posts/Day": 0.9,
            "Avg Likes": 17000,
            "Avg Comments": 220,
            "Shares/Saves": 1400,
            "PPI": 75.0,
            "ER (%)": 2.8,
            "Is Main": False,
        },
    ])
    accounts_data = [
        {"handle": "kopikenangan.id", "followers": 750_000, "avg_er": 3.4, "is_main": True},
        {"handle": "fore.coffee", "followers": 620_000, "avg_er": 2.8, "is_main": False},
    ]
    html_report = generate_executive_audit_html(
        comparison_df=comp_df,
        accounts_data=accounts_data,
        days_count=30,
        platform="Instagram",
        main_handle="kopikenangan.id",
    )
    assert len(html_report) > 1000
    assert "SocialIQ Executive Intelligence Audit" in html_report
    assert "@kopikenangan.id" in html_report
    assert "window.print()" in html_report
    assert "Rate Card" in html_report
    print(f"✓ Executive Audit Deck HTML generated successfully ({len(html_report):,} chars).")

    print("\n=== Test 7: Comparison Matrix Benchmark Fallback ===")
    from services.analytics import calculate_account_kpis, build_comparison_matrix
    from services.data_fetcher import LiveWebScraperService
    import datetime

    # Profile with real scraped followers & total posts, but 0 scraped posts (Meta bot shield active)
    shielded_account = {
        "handle": "kopikenangan.id",
        "display_name": "Kopi Kenangan",
        "followers": 755_000,
        "total_posts_lifetime": 3_957,
        "growth_rate_pct": 2.53,
        "posts": [],
        "is_main": True,
    }
    kpi = calculate_account_kpis(shielded_account, days_count=14)
    assert kpi["followers"] == 755_000
    assert kpi["avg_er"] > 0.5, f"Expected ER > 0.5%, got {kpi['avg_er']}"
    assert kpi["avg_likes"] > 1_000, f"Expected Avg Likes > 1000, got {kpi['avg_likes']}"
    assert kpi["avg_comments"] > 50, f"Expected Avg Comments > 50, got {kpi['avg_comments']}"
    assert kpi["posts_per_day"] > 0.3, f"Expected Posts/Day > 0.3, got {kpi['posts_per_day']}"
    assert kpi["is_estimated"] is True
    assert kpi["ppi"] > 35.0
    print(f"✓ Shielded Account KPI Fallback: ER={kpi['avg_er']}%, Likes={kpi['avg_likes']:,}, Comments={kpi['avg_comments']:,}, Posts/Day={kpi['posts_per_day']}, PPI={kpi['ppi']}")

    # Build comparison matrix with 3 accounts (all shielded)
    comp_accounts = [
        shielded_account,
        {
            "handle": "fore.coffee",
            "display_name": "Fore Coffee",
            "followers": 410_000,
            "total_posts_lifetime": 3_089,
            "growth_rate_pct": 1.93,
            "posts": [],
            "is_main": False,
        },
        {
            "handle": "kopijanjijiwa",
            "display_name": "Janji Jiwa",
            "followers": 586_000,
            "total_posts_lifetime": 3_028,
            "growth_rate_pct": 1.89,
            "posts": [],
            "is_main": False,
        },
    ]
    matrix_df = build_comparison_matrix(comp_accounts, days_count=14)
    assert len(matrix_df) == 3
    assert (matrix_df["Avg Likes"] > 0).all(), "Found 0 in Avg Likes!"
    assert (matrix_df["Avg Comments"] > 0).all(), "Found 0 in Avg Comments!"
    assert (matrix_df["ER (%)"] > 0).all(), "Found 0 in ER (%)!"
    assert (matrix_df["Posts/Day"] > 0).all(), "Found 0 in Posts/Day!"
    assert (matrix_df["PPI"] > 40).all(), "Found deflated PPI!"
    assert "Is Estimated" in matrix_df.columns
    print("✓ Comparison Matrix with Benchmark Fallback passed with 100% non-zero metrics:")
    for _, r in matrix_df.iterrows():
        print(f"   {r['Profile']}: Followers={r['Followers']:,}, ER={r['ER (%)']}%, Likes={r['Avg Likes']:,}, Posts/Day={r['Posts/Day']}, PPI={r['PPI']}")

    # Test _generate_smart_benchmark_posts
    scraper = LiveWebScraperService()
    start_d = datetime.date.today() - datetime.timedelta(days=14)
    end_d = datetime.date.today()
    gen_posts = scraper._generate_smart_benchmark_posts(
        handle="kopikenangan.id",
        display_name="Kopi Kenangan",
        bio="Meet our new Brand Ambassador, NCT HAECHAN 💛",
        followers=755_000,
        total_posts_lifetime=3_957,
        start_date=start_d,
        end_date=end_d,
    )
    assert len(gen_posts) >= 5, f"Expected >= 5 posts, got {len(gen_posts)}"
    assert all(p["likes"] > 0 for p in gen_posts)
    assert all(p["is_estimated"] is True for p in gen_posts)
    assert any("Reels" in p["content_type"] or "Video" in p["content_type"] for p in gen_posts)
    print(f"✓ Generated {len(gen_posts)} smart benchmark posts with contextual captions and hashtags.")

    print("\n🎉 ALL GROWTH & VIRAL SUITE TESTS PASSED!")


if __name__ == "__main__":
    test_growth_features()


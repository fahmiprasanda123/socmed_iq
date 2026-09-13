"""
SocialIQ Benchmark - Social Media Benchmarking & Analytics Dashboard
Streamlit Application Entrypoint.
"""

from __future__ import annotations
import datetime
import os
import time
from typing import Any, Dict, List
import pandas as pd
import streamlit as st

from components.charts import (
    create_follower_growth_chart,
    create_format_performance_bar,
    create_hashtag_bar,
    create_quadrant_scatter,
    create_timing_heatmap,
)
import importlib
import services.analytics
import services.data_fetcher
importlib.reload(services.analytics)
importlib.reload(services.data_fetcher)

from services.analytics import (
    analyze_content_formats,
    build_comparison_matrix,
    extract_top_hashtags,
    flatten_all_posts,
    generate_timing_heatmap_matrix,
)
from services.data_fetcher import LiveWebScraperService
from utils.helpers import (
    clean_handle,
    format_number,
    format_percent,
    to_csv_bytes,
    to_excel_bytes,
)

# Page configuration
st.set_page_config(
    page_title="SocialIQ | Social Media Benchmarking & Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for modern Analytics UI
st.markdown(
    """
    <style>
    /* Global App Styling */
    .stApp {
        background-color: #0A0F1D;
        color: #E2E8F0;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }

    /* Metric Cards */
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.4);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(99, 102, 241, 0.4);
    }
    .metric-label {
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94A3B8;
        margin-bottom: 6px;
        font-weight: 600;
    }
    .metric-value {
        font-size: 1.85rem;
        font-weight: 700;
        color: #F8FAFC;
        line-height: 1.2;
    }
    .metric-delta {
        font-size: 0.8rem;
        margin-top: 6px;
        font-weight: 500;
    }
    .delta-pos {
        color: #10B981;
    }
    .delta-neg {
        color: #F43F5E;
    }
    .delta-neu {
        color: #94A3B8;
    }

    /* Strategy Callout Banner */
    .strategy-card {
        background: linear-gradient(90deg, rgba(99, 102, 241, 0.12) 0%, rgba(16, 185, 129, 0.08) 100%);
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 20px;
    }

    /* Badges */
    .badge-pill {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-primary {
        background-color: rgba(99, 102, 241, 0.2);
        color: #818CF8;
        border: 1px solid rgba(99, 102, 241, 0.4);
    }
    .badge-success {
        background-color: rgba(16, 185, 129, 0.2);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.4);
    }

    /* Post Card */
    .post-card {
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 16px;
        transition: border-color 0.2s ease;
    }
    .post-card:hover {
        border-color: rgba(99, 102, 241, 0.5);
    }

    /* Tab styling override */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        padding-bottom: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 18px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.95rem;
        color: #94A3B8;
        background-color: transparent;
    }
    .stTabs [aria-selected="true"] {
        color: #FFFFFF !important;
        background-color: rgba(99, 102, 241, 0.2) !important;
        border: 1px solid rgba(99, 102, 241, 0.4);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Session state initialization (empty inputs by default)
if "main_acc_input" not in st.session_state or st.session_state.get("main_acc_input") == "shopee_id":
    st.session_state.main_acc_input = ""
if "comp_acc_input" not in st.session_state or "tokopedia" in st.session_state.get("comp_acc_input", ""):
    st.session_state.comp_acc_input = ""
if "platform_choice" not in st.session_state:
    st.session_state.platform_choice = "Instagram"
if "date_preset_choice" not in st.session_state:
    st.session_state.date_preset_choice = "Last 30 Days"


# Caching benchmark pipeline for instant responses
@st.cache_data(show_spinner=False, ttl=1800)
def get_benchmark_dataset(
    platform: str,
    main_account: str,
    competitors_tuple: tuple[str, ...],
    start_date: datetime.date,
    end_date: datetime.date,
) -> Dict[str, Any]:
    """
    Live web scraper benchmarking pipeline.
    """
    service = LiveWebScraperService()
    return service.fetch_benchmark_dataset(
        platform=platform,
        main_account=main_account,
        competitors=list(competitors_tuple),
        start_date=start_date,
        end_date=end_date,
    )


# --- SIDEBAR INPUTS ---
with st.sidebar:
    st.markdown(
        """
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">
            <div style="background:#6366F1; width:34px; height:34px; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:18px; font-weight:bold;">⚡</div>
            <div>
                <h2 style="margin:0; font-size:1.3rem; font-weight:800; color:#FFFFFF;">SocialIQ</h2>
                <p style="margin:0; font-size:0.75rem; color:#94A3B8;">Social Media Benchmarking & Intelligence</p>
                <p style="margin:2px 0 0 0; font-size:0.72rem; color:#818CF8;">
                    by <a href="https://threads.net/@itsamilitarysecret" target="_blank" style="color:#818CF8; text-decoration:none; font-weight:600;">threads.com/@itsamilitarysecret</a>
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # Platform selector
    platform_options = ["Instagram", "TikTok", "Threads"]
    platform_icons = {"Instagram": "📸", "TikTok": "🎵", "Threads": "🧵"}
    
    selected_platform = st.selectbox(
        "Platform",
        platform_options,
        index=platform_options.index(st.session_state.platform_choice),
        format_func=lambda x: f"{platform_icons[x]} {x}",
        key="platform_choice",
    )

    # Main Account Input
    main_acc_str = st.text_input(
        "Akun Utama (Milik Anda)",
        value=st.session_state.main_acc_input,
        placeholder="misal: akun_anda atau @akun_anda",
        help="Masukkan URL lengkap atau handle akun utama Anda.",
        key="main_acc_input",
    )

    # Competitor Accounts Input
    comp_acc_str = st.text_area(
        "Akun Kompetitor (1–5 akun, 1 per baris)",
        value=st.session_state.comp_acc_input,
        height=110,
        placeholder="kompetitor1\nkompetitor2\nkompetitor3",
        help="Masukkan 1 hingga 5 akun kompetitor untuk dibandingkan (1 per baris).",
        key="comp_acc_input",
    )

    # Date Range Selector
    date_preset = st.radio(
        "Rentang Waktu Analisis",
        ["Last 7 Days", "Last 30 Days", "Custom Range"],
        index=["Last 7 Days", "Last 30 Days", "Custom Range"].index(st.session_state.date_preset_choice),
        horizontal=True,
        key="date_preset_choice",
    )

    today = datetime.date.today()
    if date_preset == "Last 7 Days":
        start_dt = today - datetime.timedelta(days=7)
        end_dt = today
    elif date_preset == "Last 30 Days":
        start_dt = today - datetime.timedelta(days=30)
        end_dt = today
    else:
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            start_dt = st.date_input("Mulai", value=today - datetime.timedelta(days=14))
        with col_d2:
            end_dt = st.date_input("Selesai", value=today)
        if start_dt > end_dt:
            st.error("Tanggal mulai tidak boleh melebihi tanggal selesai.")
            start_dt, end_dt = end_dt, start_dt

    # Action Button
    analyze_clicked = st.button("🚀 Analyze & Benchmark", type="primary", use_container_width=True)


# Parse and clean account inputs
main_handle = clean_handle(main_acc_str)
competitors_raw = [clean_handle(line) for line in comp_acc_str.split("\n") if clean_handle(line)]
# Limit to maximum 5 competitors
competitors = competitors_raw[:5]

if not main_handle:
    st.markdown(
        """
        <div style="text-align:center; padding: 60px 20px; background: rgba(30, 41, 59, 0.4); border: 1px dashed rgba(255,255,255,0.15); border-radius: 16px; margin-top: 20px;">
            <div style="font-size: 48px; margin-bottom: 16px;">⚡</div>
            <h2 style="color: #FFFFFF; font-weight: 700; margin-bottom: 4px;">SocialIQ Benchmarking & Intelligence</h2>
            <p style="color: #818CF8; font-size: 0.85rem; font-weight: 600; margin: 0 0 16px 0;">
                by <a href="https://threads.net/@itsamilitarysecret" target="_blank" style="color:#818CF8; text-decoration:none;">threads.com/@itsamilitarysecret</a>
            </p>
            <p style="color: #94A3B8; max-width: 540px; margin: 0 auto 24px auto; font-size: 0.95rem; line-height: 1.6;">
                Bandingkan performa akun media sosial Anda dengan kompetitor secara mendalam (Engagement Rate, Follower Growth, Efficiency Quadrant, Best Posting Time, & Keyword Intelligence).
            </p>
            <div style="display: inline-block; background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 8px; padding: 12px 24px; color: #A5B4FC; font-size: 0.9rem;">
                👈 <b>Langkah Awal:</b> Masukkan <b>Akun Utama</b> dan akun kompetitor di sidebar sebelah kiri, lalu klik <b>Analyze & Benchmark</b>.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# Execution with Streamlit Status Indicator
status_box = st.empty()

with st.status(f"⚡ Melakukan live scraping untuk @{main_handle} vs {len(competitors)} kompetitor...", expanded=False) as status:
    st.write(f"1. Mengambil data live profil {selected_platform} untuk @{main_handle}...")
    time.sleep(0.1)
    st.write(f"2. Mengambil data follower, total post, dan metrik kompetitor...")
    
    benchmark_data = get_benchmark_dataset(
        platform=selected_platform,
        main_account=main_handle,
        competitors_tuple=tuple(competitors),
        start_date=start_dt,
        end_date=end_dt,
    )
    
    st.write("3. Menghitung Engagement Rate (ER) tier, Page Performance Index (PPI), dan Follower Trajectory...")
    time.sleep(0.1)
    st.write("4. Menyusun matriks perbandingan, kuadran efisiensi, dan keyword intelligence...")
    status.update(label="✅ Live Web Scraping Selesai!", state="complete", expanded=False)

accounts_data = benchmark_data.get("accounts", [])
days_count = benchmark_data.get("date_range", {}).get("days", 30)

# Build analytics DataFrames
comparison_df = build_comparison_matrix(accounts_data, days_count)
posts_df = flatten_all_posts(accounts_data)

# Extract main account row and competitor averages
main_row = comparison_df[comparison_df["Is Main"] == True]
comp_rows = comparison_df[comparison_df["Is Main"] == False]

if not main_row.empty:
    main_kpi = main_row.iloc[0]
else:
    main_kpi = comparison_df.iloc[0]

# Calculate competitor benchmark averages for delta badges
avg_comp_followers = comp_rows["Followers"].mean() if not comp_rows.empty else main_kpi["Followers"]
avg_comp_growth = comp_rows["Growth (%)"].mean() if not comp_rows.empty else main_kpi["Growth (%)"]
avg_comp_er = comp_rows["ER (%)"].mean() if not comp_rows.empty else main_kpi["ER (%)"]
avg_comp_posts = comp_rows["Total Posts"].mean() if not comp_rows.empty else main_kpi["Total Posts"]

# --- APP HEADER BANNER ---
st.markdown(
    f"""
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; margin-bottom:18px; padding:12px 18px; background:rgba(30, 41, 59, 0.5); border:1px solid rgba(255,255,255,0.08); border-radius:12px;">
        <div style="display:flex; align-items:center; gap:12px;">
            <span class="badge-pill badge-primary">{selected_platform.upper()}</span>
            <span style="font-size:1.25rem; font-weight:700; color:#FFFFFF;">@{main_handle}</span>
            <span style="color:#94A3B8; font-size:0.9rem;">vs {len(competitors)} Kompetitor</span>
        </div>
        <div style="color:#94A3B8; font-size:0.85rem;">
            📅 Rentang: <b style="color:#CBD5E1;">{start_dt.strftime('%d %b %Y')} – {end_dt.strftime('%d %b %Y')}</b> ({days_count} hari)
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- TABS NAVIGATION ---
tab_overview, tab_quadrant, tab_timing, tab_content = st.tabs([
    "📊 Benchmark Matrix (Overview)",
    "🎯 Efficiency & Quadrant",
    "⏰ Content Timing (Heatmap)",
    "💡 Content & Keyword Intelligence",
])


# ==============================================================================
# TAB 1: BENCHMARK MATRIX (OVERVIEW)
# ==============================================================================
with tab_overview:
    # 1. Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    
    # Delta calculations
    diff_followers = main_kpi["Followers"] - avg_comp_followers
    diff_growth = main_kpi["Growth (%)"] - avg_comp_growth
    diff_er = main_kpi["ER (%)"] - avg_comp_er
    diff_posts = main_kpi["Total Posts"] - avg_comp_posts

    def render_delta_html(diff: float, is_pct: bool = False, suffix: str = "vs Avg") -> str:
        sign = "+" if diff > 0 else ""
        css_class = "delta-pos" if diff > 0 else ("delta-neg" if diff < 0 else "delta-neu")
        val_str = f"{sign}{diff:.2f}%" if is_pct else f"{sign}{format_number(diff)}"
        return f"<div class='metric-delta {css_class}'>{val_str} {suffix}</div>"

    with c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">👥 Total Followers</div>
                <div class="metric-value">{format_number(main_kpi['Followers'])}</div>
                {render_delta_html(diff_followers)}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">📈 Follower Growth</div>
                <div class="metric-value">{format_percent(main_kpi['Growth (%)'])}</div>
                {render_delta_html(diff_growth, is_pct=True)}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">⚡ Avg Engagement (ER)</div>
                <div class="metric-value">{format_percent(main_kpi['ER (%)'])}</div>
                {render_delta_html(diff_er, is_pct=True)}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">📮 Total Posts ({days_count}d)</div>
                <div class="metric-value">{main_kpi['Total Posts']}</div>
                {render_delta_html(diff_posts, suffix='vs Avg Freq')}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)

    # 2. Comparison Table
    col_t_header, col_export = st.columns([3, 1])
    with col_t_header:
        st.subheader("📋 Comparison Matrix")
        st.caption("Perbandingan komprehensif metrik utama akun Anda dengan kompetitor.")
    
    # Format display DataFrame
    display_df = comparison_df[[
        "Profile", "Followers", "Growth (%)", "Total Posts", "Posts/Day", 
        "Avg Likes", "Avg Comments", "Shares/Saves", "PPI", "ER (%)"
    ]].copy()

    # Downloads
    with col_export:
        col_csv, col_xlsx = st.columns(2)
        with col_csv:
            csv_bytes = to_csv_bytes(display_df)
            st.download_button(
                label="📥 CSV",
                data=csv_bytes,
                file_name=f"benchmark_{selected_platform.lower()}_{main_handle}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with col_xlsx:
            xlsx_bytes = to_excel_bytes(display_df)
            st.download_button(
                label="📊 Excel",
                data=xlsx_bytes,
                file_name=f"benchmark_{selected_platform.lower()}_{main_handle}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    # Render styled dataframe
    try:
        st.dataframe(
            display_df.style.format({
                "Followers": "{:,.0f}",
                "Growth (%)": "{:+.2f}%",
                "Total Posts": "{:,.0f}",
                "Posts/Day": "{:.2f}",
                "Avg Likes": "{:,.0f}",
                "Avg Comments": "{:,.0f}",
                "Shares/Saves": "{:,.0f}",
                "PPI": "{:.1f}",
                "ER (%)": "{:.2f}%",
            }).background_gradient(subset=["PPI", "ER (%)"], cmap="BuPu"),
            use_container_width=True,
            height=220,
        )
    except Exception:
        st.dataframe(
            display_df.style.format({
                "Followers": "{:,.0f}",
                "Growth (%)": "{:+.2f}%",
                "Total Posts": "{:,.0f}",
                "Posts/Day": "{:.2f}",
                "Avg Likes": "{:,.0f}",
                "Avg Comments": "{:,.0f}",
                "Shares/Saves": "{:,.0f}",
                "PPI": "{:.1f}",
                "ER (%)": "{:.2f}%",
            }),
            use_container_width=True,
            height=220,
        )

    st.caption("ℹ️ **PPI (Page Performance Index)**: Skor komposit 0–100 menggabungkan Engagement Rate (60%) dan Follower Growth Rate (40%).")

    # 3. Follower Growth Trajectory Chart
    st.markdown("---")
    st.plotly_chart(create_follower_growth_chart(accounts_data), use_container_width=True)


# ==============================================================================
# TAB 2: EFFICIENCY & QUADRANT (SCATTER PLOT)
# ==============================================================================
with tab_quadrant:
    st.subheader("🎯 Efficiency Quadrant Matrix")
    st.caption("Analisis posisi efisiensi konten: Frekuensi Posting vs. Tingkat Keterlibatan (Engagement Rate).")

    # Strategy explanation banner
    st.markdown(
        """
        <div class="strategy-card">
            <div style="font-weight:700; color:#FFFFFF; margin-bottom:4px;">🧭 Panduan 4 Kuadran Efisiensi:</div>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:12px; margin-top:8px; font-size:0.84rem;">
                <div><b style="color:#10B981;">✨ High Efficiency:</b> Posting hemat/terukur namun ER tinggi. Audiens sangat setia.</div>
                <div><b style="color:#6366F1;">🏆 Powerhouses:</b> Posting agresif dan ER tetap tinggi. Penguasa pasar dengan tim konten solid.</div>
                <div><b style="color:#F59E0B;">⚠️ Spamming / Fatigue:</b> Terlalu sering posting namun respon audiens rendah. Risiko kejenuhan.</div>
                <div><b style="color:#94A3B8;">💤 Low Impact:</b> Jarang posting dan ER rendah. Perlu revitalisasi strategi konten.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 4-Quadrant Plotly Scatter
    st.plotly_chart(create_quadrant_scatter(comparison_df, main_handle), use_container_width=True)

    # Automatic Diagnostic & Strategic Recommendation Card
    x_med = comparison_df["Posts/Day"].median()
    y_med = comparison_df["ER (%)"].median()
    main_freq = main_kpi["Posts/Day"]
    main_er = main_kpi["ER (%)"]

    is_high_freq = main_freq >= x_med
    is_high_er = main_er >= y_med

    if is_high_er and not is_high_freq:
        quadrant_name = "✨ High Efficiency (Niche Performer)"
        rec_text = "Akun Anda memiliki engagement rate di atas rata-rata industri dengan kuantitas posting yang terukur. **Rekomendasi:** Anda memiliki ruang untuk bereksperimen menambah 1–2 postingan berkualitas per minggu untuk memperluas jangkauan organik tanpa menurunkan engagement."
    elif is_high_er and is_high_freq:
        quadrant_name = "🏆 Powerhouses (Market Leader)"
        rec_text = "Akun Anda berada di posisi dominan! Konsistensi tinggi diimbangi oleh respon audiens yang sangat antusias. **Rekomendasi:** Pertahankan pilar konten juara dan manfaatkan momentum ini untuk meluncurkan kampanye konversi produk langsung."
    elif not is_high_er and is_high_freq:
        quadrant_name = "⚠️ Spamming / Audience Fatigue"
        rec_text = "Frekuensi posting akun Anda di atas median, namun tingkat interaksi audiens berada di bawah rata-rata. **Rekomendasi:** Kurangi volume postingan harian. Fokus pada kualitas visual, storytelling, dan format Carousel/Reels yang memicu interaksi aktif (saves & shares)."
    else:
        quadrant_name = "💤 Low Impact"
        rec_text = "Frekuensi dan engagement rate akun Anda saat ini berada di bawah median kompetitor. **Rekomendasi:** Lakukan audit konten kompetitor di Tab 4 untuk melihat pilar topik dan hashtag terbaik, lalu tingkatkan jadwal posting minimal 1x per hari di jam optimal (Tab 3)."

    st.markdown(
        f"""
        <div style="background:rgba(15, 23, 42, 0.9); border:1px solid rgba(99, 102, 241, 0.3); border-radius:12px; padding:18px 22px; margin-top:10px;">
            <div style="font-size:0.8rem; text-transform:uppercase; color:#818CF8; font-weight:700;">Status Diagnostik Akun Anda</div>
            <div style="font-size:1.15rem; font-weight:700; color:#FFFFFF; margin:4px 0 8px 0;">{quadrant_name}</div>
            <p style="margin:0; font-size:0.9rem; color:#CBD5E1; line-height:1.5;">{rec_text}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ==============================================================================
# TAB 3: CONTENT TIMING (HEATMAP)
# ==============================================================================
with tab_timing:
    st.subheader("⏰ Content Timing (Best Time to Post)")
    st.caption("Peta intensitas interaksi 7 Hari x 24 Jam untuk menemukan jendela waktu posting paling menguntungkan.")

    # Filter selector
    all_account_choices = ["All Accounts"] + [acc["handle"] for acc in accounts_data]
    col_acc_filter, col_metric_filter = st.columns([2, 2])
    
    with col_acc_filter:
        selected_timing_acc = st.selectbox(
            "Pilih Profil untuk Dianalisis",
            all_account_choices,
            format_func=lambda x: f"Semua Profil (Aggregated)" if x == "All Accounts" else f"@{x} " + ("(You)" if x == main_handle else ""),
        )

    with col_metric_filter:
        timing_metric = st.selectbox(
            "Metrik Intensitas Heatmap",
            ["interactions", "post_count"],
            format_func=lambda x: "Rata-rata Interaksi per Post" if x == "interactions" else "Kepadatan Jumlah Postingan",
        )

    # Generate Heatmap Matrix
    heatmap_matrix, peak_info = generate_timing_heatmap_matrix(
        posts_df,
        target_account=selected_timing_acc,
        metric=timing_metric,
    )

    # Best time recommendation callout
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:16px; background:linear-gradient(90deg, rgba(245, 158, 11, 0.15) 0%, rgba(99, 102, 241, 0.1) 100%); border:1px solid rgba(245, 158, 11, 0.4); border-radius:12px; padding:16px 20px; margin:14px 0 20px 0;">
            <div style="font-size:28px;">⭐</div>
            <div>
                <div style="font-size:0.8rem; text-transform:uppercase; color:#FCD34D; font-weight:700;">Rekomendasi Waktu Posting Optimal</div>
                <div style="font-size:1.1rem; font-weight:700; color:#FFFFFF;">
                    Hari {peak_info['day']}, Pukul {peak_info['hour_label']}
                </div>
                <div style="font-size:0.85rem; color:#E2E8F0;">
                    Slot ini menghasilkan rata-rata tertinggi sebesar <b style="color:#FCD34D;">{format_number(peak_info['value'])} interaksi</b> per postingan!
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Heatmap Plotly Chart
    chart_title = f"Heatmap Intensitas Interaksi ({selected_timing_acc})" if selected_timing_acc != "All Accounts" else "Heatmap Intensitas Interaksi Seluruh Akun"
    st.plotly_chart(
        create_timing_heatmap(heatmap_matrix, peak_info, title=chart_title),
        use_container_width=True,
    )


# ==============================================================================
# TAB 4: CONTENT & KEYWORD INTELLIGENCE
# ==============================================================================
with tab_content:
    st.subheader("💡 Content & Keyword Intelligence")
    st.caption("Eksplorasi format konten paling efektif, leaderboard postingan terbaik, dan analisis hashtag.")

    # 1. Format Performance Bar
    format_summary_df = analyze_content_formats(posts_df)
    
    col_fmt1, col_fmt2 = st.columns([3, 2])
    with col_fmt1:
        st.plotly_chart(create_format_performance_bar(format_summary_df), use_container_width=True)
    with col_fmt2:
        st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
        st.markdown("**Performa Format Konten (Tabel):**")
        if not format_summary_df.empty:
            st.dataframe(
                format_summary_df[[
                    "content_type", "total_posts", "avg_interactions", "avg_likes", "avg_comments", "avg_er"
                ]].rename(columns={
                    "content_type": "Format",
                    "total_posts": "Posts",
                    "avg_interactions": "Avg Interaksi",
                    "avg_likes": "Likes",
                    "avg_comments": "Komen",
                    "avg_er": "ER (%)",
                }).style.format({
                    "Posts": "{:,.0f}",
                    "Avg Interaksi": "{:,.0f}",
                    "Likes": "{:,.0f}",
                    "Komen": "{:,.0f}",
                    "ER (%)": "{:.2f}%",
                }),
                use_container_width=True,
                height=180,
            )

    st.markdown("---")

    # 2. Top Performing Posts Leaderboard
    st.subheader("🏆 Top Performing Posts Leaderboard")
    
    col_f_acc, col_f_sort = st.columns([2, 2])
    with col_f_acc:
        filter_post_acc = st.selectbox(
            "Filter Berdasarkan Akun",
            ["All Profiles"] + [acc["handle"] for acc in accounts_data],
            key="filter_posts_acc",
        )
    with col_f_sort:
        sort_by_metric = st.selectbox(
            "Urutkan Berdasarkan",
            ["total_interactions", "post_er", "likes", "comments", "shares"],
            format_func=lambda x: {
                "total_interactions": "Total Interaksi Tertinggi",
                "post_er": "Engagement Rate (ER) Tertinggi",
                "likes": "Jumlah Likes Terbanyak",
                "comments": "Jumlah Komentar Terbanyak",
                "shares": "Jumlah Shares/Saves Terbanyak",
            }[x],
        )

    # Filter and sort posts
    ranked_posts_df = posts_df.copy()
    if filter_post_acc != "All Profiles":
        ranked_posts_df = ranked_posts_df[ranked_posts_df["account"] == filter_post_acc]
    
    if not ranked_posts_df.empty:
        ranked_posts_df = ranked_posts_df.sort_values(by=sort_by_metric, ascending=False).head(9)
        
        # Display posts in a 3-column grid
        post_cols = st.columns(3)
        for idx, (_, post_row) in enumerate(ranked_posts_df.iterrows()):
            col_target = post_cols[idx % 3]
            with col_target:
                caption_text = post_row.get("caption", "")
                if len(caption_text) > 130:
                    caption_text = caption_text[:130] + "..."

                is_main_post = post_row.get("is_main", False)
                handle_badge = f"<span class='badge-pill badge-primary'>@{post_row['account']}</span>" if is_main_post else f"<span class='badge-pill' style='background:rgba(255,255,255,0.1); color:#CBD5E1;'>@{post_row['account']}</span>"
                post_date_display = post_row.get("date") or (str(post_row.get("timestamp", ""))[:10] if post_row.get("timestamp") else "-")

                st.markdown(
                    f"""
                    <div class="post-card">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                            {handle_badge}
                            <span style="font-size:0.75rem; color:#94A3B8;">{post_date_display}</span>
                        </div>
                        <img src="{post_row['thumbnail_url']}" style="width:100%; height:160px; object-fit:cover; border-radius:8px; margin-bottom:10px;" />
                        <div style="font-size:0.82rem; color:#E2E8F0; line-height:1.4; margin-bottom:12px; min-height:48px;">
                            {caption_text}
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.8rem; background:rgba(30,41,59,0.5); padding:8px 10px; border-radius:8px;">
                            <span>❤️ <b>{format_number(post_row['likes'])}</b></span>
                            <span>💬 <b>{format_number(post_row['comments'])}</b></span>
                            <span>🔁 <b>{format_number(post_row['shares'])}</b></span>
                            <span style="color:#10B981; font-weight:700;">⚡ {post_row['post_er']:.2f}%</span>
                        </div>
                        <div style="margin-top:10px; text-align:right;">
                            <a href="{post_row['post_url']}" target="_blank" style="font-size:0.78rem; color:#818CF8; text-decoration:none; font-weight:600;">Lihat Postingan Asli ↗</a>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        st.info("Tidak ada data postingan yang cocok dengan kriteria filter.")

    st.markdown("---")

    # 3. Hashtag & Keyword Intelligence
    st.subheader("🏷️ Hashtag & Keyword Intelligence")
    st.caption("Analisis topik dan tagar yang mendatangkan engagement rata-rata paling tinggi di antara seluruh akun.")

    hashtag_df = extract_top_hashtags(posts_df, top_n=15)
    
    col_h_chart, col_h_table = st.columns([3, 2])
    with col_h_chart:
        st.plotly_chart(create_hashtag_bar(hashtag_df), use_container_width=True)
    with col_h_table:
        st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
        st.markdown("**Hashtag Leaderboard (Tabel):**")
        if not hashtag_df.empty:
            st.dataframe(
                hashtag_df.rename(columns={
                    "hashtag": "Tagar",
                    "count": "Frekuensi",
                    "total_interactions": "Total Interaksi",
                    "avg_interactions": "Avg Interaksi",
                    "avg_er": "Avg ER (%)",
                }).style.format({
                    "Frekuensi": "{:,.0f}",
                    "Total Interaksi": "{:,.0f}",
                    "Avg Interaksi": "{:,.0f}",
                    "Avg ER (%)": "{:.2f}%",
                }),
                use_container_width=True,
                height=350,
            )
        else:
            st.info("Belum ada hashtag terdeteksi pada dataset ini.")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align:center; font-size:0.8rem; color:#64748B; padding:10px 0 20px 0;">
        ⚡ <b>SocialIQ Benchmarking System</b> — Social Intelligence • Built with Python & Streamlit • by <a href="https://threads.net/@itsamilitarysecret" target="_blank" style="color:#818CF8; text-decoration:none; font-weight:600;">threads.com/@itsamilitarysecret</a>
    </div>
    """,
    unsafe_allow_html=True,
)

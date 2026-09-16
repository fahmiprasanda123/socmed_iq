"""
SocialIQ Benchmark - Social Media Benchmarking & Analytics Dashboard
Streamlit Application Entrypoint.
All data is sourced from live web scraping — no synthetic/fake data.
"""

from __future__ import annotations
import datetime
import html as html_module
import time
from typing import Any, Dict, List
import pandas as pd
import streamlit as st

import importlib

import components.charts
try:
    importlib.reload(components.charts)
except Exception:
    pass

try:
    from components.charts import (
        create_follower_growth_chart,
        create_format_performance_bar,
        create_hashtag_bar,
        create_quadrant_scatter,
        create_timing_heatmap,
        create_wordcloud_figure,
    )
except ImportError:
    from components.charts import (
        create_follower_growth_chart,
        create_format_performance_bar,
        create_hashtag_bar,
        create_quadrant_scatter,
        create_timing_heatmap,
    )
    def create_wordcloud_figure(frequencies, *args, **kwargs):
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(9, 4.2), facecolor="#0B1120")
        ax.text(0.5, 0.5, "Silakan Rerun aplikasi untuk memuat WordCloud", color="#94A3B8", ha="center", va="center")
        ax.axis("off")
        return fig

import services.analytics
try:
    importlib.reload(services.analytics)
except Exception:
    pass

try:
    from services.analytics import (
        analyze_content_formats,
        build_comparison_matrix,
        extract_top_hashtags,
        flatten_all_posts,
        generate_timing_heatmap_matrix,
        generate_wordcloud_frequencies,
    )
except ImportError:
    from services.analytics import (
        analyze_content_formats,
        build_comparison_matrix,
        extract_top_hashtags,
        flatten_all_posts,
        generate_timing_heatmap_matrix,
    )
    def generate_wordcloud_frequencies(*args, **kwargs):
        return {}

import services.data_fetcher
try:
    importlib.reload(services.data_fetcher)
except Exception:
    pass

from services.data_fetcher import LiveWebScraperService, _generate_dynamic_account_card
from services.storage import storage_service
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

    /* No data notice */
    .no-data-notice {
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.25);
        border-radius: 10px;
        padding: 10px 14px;
        font-size: 0.82rem;
        color: #FCD34D;
        margin-top: 8px;
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


def _escape_html(text: str) -> str:
    """Escape user-supplied text before injecting into HTML to prevent XSS."""
    return html_module.escape(str(text)) if text else ""


def _is_safe_url(url: str) -> bool:
    """Validate that a URL is safe for use in href/src attributes."""
    if not url:
        return False
    safe_prefixes = ("https://", "http://", "data:image/")
    return url.startswith(tuple(safe_prefixes))


# Session state initialization (clean, no hardcoded values)
if "main_acc_input" not in st.session_state:
    st.session_state.main_acc_input = ""
if "comp_acc_input" not in st.session_state:
    st.session_state.comp_acc_input = ""
if "platform_choice" not in st.session_state:
    st.session_state.platform_choice = "Instagram"
if "date_preset_choice" not in st.session_state:
    st.session_state.date_preset_choice = "Last 30 Days"
if "benchmark_result" not in st.session_state:
    st.session_state.benchmark_result = None
if "last_analysis_params" not in st.session_state:
    st.session_state.last_analysis_params = None
if "toggle_enable_backfill" not in st.session_state:
    st.session_state.toggle_enable_backfill = True


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
        format_func=lambda x: f"{platform_icons[x]} {x}",
        key="platform_choice",
    )

    # Main Account Input
    main_acc_str = st.text_input(
        "Akun Utama (Milik Anda)",
        placeholder="misal: akun_anda atau @akun_anda",
        help="Masukkan URL lengkap atau handle akun utama Anda.",
        key="main_acc_input",
    )

    # Competitor Accounts Input
    comp_acc_str = st.text_area(
        "Akun Kompetitor (1–5 akun, 1 per baris)",
        height=110,
        placeholder="kompetitor1\nkompetitor2\nkompetitor3",
        help="Masukkan 1 hingga 5 akun kompetitor untuk dibandingkan (1 per baris).",
        key="comp_acc_input",
    )

    # Date Range Selector
    date_preset = st.radio(
        "Rentang Waktu Analisis",
        ["Last 7 Days", "Last 30 Days", "Custom Range"],
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

    st.markdown("---")

    # Historical Tracking & Data Management Expander
    with st.expander("🗄️ Manajemen Data Historis", expanded=False):
        enable_backfill = st.toggle(
            "Smart Backfill Estimasi",
            value=True,
            help="Jika diaktifkan, sistem mengestimasi tren kurva pertumbuhan organik ke belakang saat data riwayat database belum mencapai 7 hari. Data ini akan otomatis tergantikan seiring berjalannya hari.",
            key="toggle_enable_backfill",
        )

        st.markdown("<p style='font-size:0.8rem; font-weight:600; color:#E2E8F0; margin:10px 0 4px 0;'>📥 Upload Riwayat (CSV / Excel)</p>", unsafe_allow_html=True)
        uploaded_history = st.file_uploader(
            "File CSV/Excel",
            type=["csv", "xlsx", "xls"],
            label_visibility="collapsed",
            help="Format minimal: kolom date, handle, followers. Kolom opsional: following, total_posts, avg_er",
            key="history_file_uploader",
        )
        if uploaded_history is not None:
            if st.button("💾 Simpan ke Database", use_container_width=True, key="btn_save_import"):
                ok, msg, count = storage_service.import_history_file(
                    uploaded_history.getvalue(),
                    uploaded_history.name,
                )
                if ok:
                    st.success(f"✅ {msg}")
                    st.session_state.benchmark_result = None
                else:
                    st.error(f"❌ {msg}")

        st.markdown("<p style='font-size:0.8rem; font-weight:600; color:#E2E8F0; margin:12px 0 4px 0;'>📄 Template & Backup</p>", unsafe_allow_html=True)
        c_tpl, c_exp = st.columns(2)
        with c_tpl:
            tpl_bytes = storage_service.get_sample_template_bytes(file_format="xlsx")
            st.download_button(
                "📥 Template",
                data=tpl_bytes,
                file_name="socialiq_template_historis.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                help="Unduh contoh format file Excel untuk input data historis",
            )
        with c_exp:
            export_df = storage_service.export_history_df()
            if not export_df.empty:
                exp_bytes = to_excel_bytes(export_df)
                st.download_button(
                    "📤 Backup DB",
                    data=exp_bytes,
                    file_name=f"socialiq_db_backup_{datetime.date.today().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    help="Unduh seluruh data snapshot yang tersimpan di SQLite",
                )
            else:
                st.button("📤 Backup DB", disabled=True, use_container_width=True, help="Belum ada data di database")


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


# --- GATED EXECUTION: Only run scraping when Analyze button is clicked ---
current_params = (selected_platform, main_handle, tuple(competitors), str(start_dt), str(end_dt))

if analyze_clicked:
    # User clicked analyze — run scraping
    with st.status(f"⚡ Melakukan live scraping untuk @{_escape_html(main_handle)} vs {len(competitors)} kompetitor...", expanded=False) as status:
        st.write(f"1. Mengambil data live profil {selected_platform} untuk @{_escape_html(main_handle)}...")
        time.sleep(0.1)
        st.write(f"2. Mengambil data follower, total post, dan metrik kompetitor...")
        
        scraper = LiveWebScraperService(enable_backfill=enable_backfill)
        benchmark_data = scraper.fetch_benchmark_dataset(
            platform=selected_platform,
            main_account=main_handle,
            competitors=list(competitors),
            start_date=start_dt,
            end_date=end_dt,
            enable_backfill=enable_backfill,
        )
        
        st.write("3. Menghitung Engagement Rate (ER), Page Performance Index (PPI), dan metrik lainnya...")
        time.sleep(0.1)
        st.write("4. Menyusun matriks perbandingan dan visualisasi...")
        status.update(label="✅ Live Web Scraping Selesai!", state="complete", expanded=False)
    
    # Store result in session state
    st.session_state.benchmark_result = benchmark_data
    st.session_state.last_analysis_params = current_params

elif st.session_state.benchmark_result is not None:
    # Use cached result from previous analysis
    benchmark_data = st.session_state.benchmark_result
else:
    # No analysis has been run yet — prompt user
    st.markdown(
        f"""
        <div style="text-align:center; padding: 40px 20px; background: rgba(30, 41, 59, 0.4); border: 1px dashed rgba(255,255,255,0.15); border-radius: 16px; margin-top: 20px;">
            <div style="font-size: 36px; margin-bottom: 12px;">🔍</div>
            <h3 style="color: #FFFFFF; font-weight: 700; margin-bottom: 8px;">Siap Menganalisis @{_escape_html(main_handle)}</h3>
            <p style="color: #94A3B8; font-size: 0.9rem;">
                Klik tombol <b style="color: #818CF8;">🚀 Analyze & Benchmark</b> di sidebar untuk memulai live scraping.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

accounts_data = benchmark_data.get("accounts", [])
days_count = benchmark_data.get("date_range", {}).get("days", 30)

# Check for not found accounts and display informative alert
not_found_accounts = [acc["handle"] for acc in accounts_data if acc.get("not_found")]
blocked_accounts = [acc["handle"] for acc in accounts_data if acc.get("is_blocked")]

if blocked_accounts:
    st.error(
        f"🛡️ **Akses Dibatasi oleh {selected_platform} (Cloud/Datacenter IP Block):**<br>"
        f"Server hosting (Streamlit Cloud / AWS) dibatasi oleh sistem anti-bot {selected_platform} saat mengambil data "
        f"{', '.join(['@' + _escape_html(h) for h in blocked_accounts])}. Akun ini sebenarnya ada dan aktif.<br><br>"
        "💡 **Solusi Praktis:**<br>"
        "1. **Gunakan Fitur Data Historis (Rekomendasi):** Jalankan scraping di komputer lokal Anda (IP residential), lalu gunakan menu "
        "<b>📁 Manajemen Data Historis</b> di sidebar untuk download database (.db) atau export CSV, kemudian upload di Streamlit Cloud.<br>"
        "2. **Konfigurasi Proxy:** Tambahkan `PROXY_URL = \"http://user:pass@host:port\"` di menu <i>Settings &rarr; Secrets</i> Streamlit Cloud.",
    )

if not_found_accounts:
    st.warning(
        f"⚠️ **Akun tidak ditemukan:** {', '.join(['@' + _escape_html(h) for h in not_found_accounts])} tidak terdaftar atau tidak aktif di {selected_platform}. "
        "Pastikan ejaan username sudah benar."
    )

# Check for accounts without real post metrics
no_metrics_accounts = [
    acc["handle"] for acc in accounts_data 
    if not acc.get("not_found") and not acc.get("has_real_post_metrics", False)
]
if no_metrics_accounts:
    st.info(
        f"ℹ️ **Data post terbatas:** Metrik likes/comments untuk {', '.join(['@' + _escape_html(h) for h in no_metrics_accounts])} "
        "belum dapat diambil dari scraping. Engagement Rate dan metrik interaksi mungkin menampilkan 0. "
        "Hal ini bisa terjadi jika Instagram membatasi akses data publik."
    )

# Build analytics DataFrames
comparison_df = build_comparison_matrix(accounts_data, days_count)
posts_df = flatten_all_posts(accounts_data)

if comparison_df.empty:
    st.error("Tidak ada data akun yang berhasil di-scrape. Pastikan username sudah benar dan coba lagi.")
    st.stop()

# Extract main account row and competitor averages
main_row = comparison_df.loc[comparison_df["Is Main"].eq(True)]
comp_rows = comparison_df.loc[comparison_df["Is Main"].eq(False)]

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
            <span class="badge-pill badge-primary">{_escape_html(selected_platform.upper())}</span>
            <span style="font-size:1.25rem; font-weight:700; color:#FFFFFF;">@{_escape_html(main_handle)}</span>
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
        if comp_rows.empty:
            return "<div class='metric-delta delta-neu'>— (tidak ada kompetitor)</div>"
        sign = "+" if diff > 0 else ""
        css_class = "delta-pos" if diff > 0 else ("delta-neg" if diff < 0 else "delta-neu")
        val_str = f"{sign}{diff:.2f}%" if is_pct else f"{sign}{format_number(diff)}"
        return f"<div class='metric-delta {css_class}'>{val_str} {_escape_html(suffix)}</div>"

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
        # Determine if growth data is real or estimated
        main_history_source = next(
            (acc.get("history_source", "flat") for acc in accounts_data if acc.get("is_main")),
            "flat",
        )
        show_growth_warning = (main_kpi["Growth (%)"] == 0.0 and main_history_source == "flat")
        growth_notice_html = (
            '<div class="no-data-notice">⚠️ Data historis tidak tersedia — pertumbuhan hanya bisa diukur jika ada snapshot sebelumnya.</div>'
            if show_growth_warning else ""
        )
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">📈 Follower Growth</div>
                <div class="metric-value">{format_percent(main_kpi['Growth (%)'])}</div>
                {render_delta_html(diff_growth, is_pct=True)}
                {growth_notice_html}
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
                <div class="metric-label">📮 Scraped Posts</div>
                <div class="metric-value">{main_kpi['Total Posts']}</div>
                {render_delta_html(diff_posts, suffix='vs Avg')}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)

    # 2. Comparison Table
    col_t_header, col_export = st.columns([3, 1])
    with col_t_header:
        st.subheader("📋 Comparison Matrix")
        st.caption("Perbandingan komprehensif metrik utama akun Anda dengan kompetitor. Data berasal dari live scraping.")
    
    # Format display DataFrame
    col_period_posts = f"Posts (Scraped)"
    display_df = comparison_df[[
        "Profile", "Followers", "Growth (%)", "Lifetime Posts", "Total Posts", "Posts/Day", 
        "Avg Likes", "Avg Comments", "Shares/Saves", "PPI", "ER (%)"
    ]].rename(columns={
        "Lifetime Posts": "Total Posts (Profil)",
        "Total Posts": col_period_posts,
    }).copy()

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
    fmt_dict = {
        "Followers": "{:,.0f}",
        "Growth (%)": "{:+.2f}%",
        "Total Posts (Profil)": "{:,.0f}",
        col_period_posts: "{:,.0f}",
        "Posts/Day": "{:.2f}",
        "Avg Likes": "{:,.0f}",
        "Avg Comments": "{:,.0f}",
        "Shares/Saves": "{:,.0f}",
        "PPI": "{:.1f}",
        "ER (%)": "{:.2f}%",
    }
    try:
        st.dataframe(
            display_df.style.format(fmt_dict).background_gradient(subset=["PPI", "ER (%)"], cmap="BuPu"),
            use_container_width=True,
            height=220,
        )
    except Exception:
        st.dataframe(
            display_df.style.format(fmt_dict),
            use_container_width=True,
            height=220,
        )

    st.caption("ℹ️ **PPI (Page Performance Index)**: Skor komposit 0–100 menggabungkan Engagement Rate (60%) dan Follower Growth Rate (40%).")

    # 3. Follower Growth Trajectory Chart
    st.markdown("---")

    has_db_history = any(acc.get("history_source") == "database" for acc in accounts_data)
    has_backfill = any(acc.get("history_source") == "smart_backfill" for acc in accounts_data)

    if has_db_history:
        st.markdown(
            """
            <div style="display:inline-flex; align-items:center; gap:8px; background:rgba(16, 185, 129, 0.15); border:1px solid rgba(16, 185, 129, 0.4); border-radius:8px; padding:6px 14px; font-size:0.83rem; color:#6EE7B7; margin-bottom:12px;">
                <span>🟢</span> <b>Data Riil Database</b> — Menggunakan riwayat snapshot harian yang tersimpan di SQLite / file import.
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif has_backfill:
        st.markdown(
            """
            <div style="display:inline-flex; align-items:center; gap:8px; background:rgba(245, 158, 11, 0.15); border:1px solid rgba(245, 158, 11, 0.4); border-radius:8px; padding:6px 14px; font-size:0.83rem; color:#FCD34D; margin-bottom:12px;">
                <span>⚡</span> <b>Mode Smart Backfill Aktif</b> — Menampilkan estimasi kurva pertumbuhan organik karena akun baru pertama kali dianalisis. Snapshot harian otomatis disimpan ke database dan akan menggantikan estimasi ini seiring berjalannya waktu.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.plotly_chart(create_follower_growth_chart(accounts_data), use_container_width=True)
    st.caption("ℹ️ Grafik menunjukkan lintasan pertumbuhan follower harian antar akun dalam periode analisis.")


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
    active_accounts = comparison_df[comparison_df["Posts/Day"] > 0]
    if not active_accounts.empty:
        x_med = active_accounts["Posts/Day"].median()
        y_med = active_accounts["ER (%)"].median()
    else:
        x_med = 0
        y_med = 0
    
    main_freq = main_kpi["Posts/Day"]
    main_er = main_kpi["ER (%)"]

    if main_freq == 0 and main_er == 0:
        quadrant_name = "ℹ️ Data Belum Tersedia"
        rec_text = "Metrik post untuk akun Anda belum berhasil di-scrape. Coba analisis ulang atau periksa apakah akun memiliki postingan publik yang bisa diakses."
    else:
        is_high_freq = main_freq >= x_med if x_med > 0 else False
        is_high_er = main_er >= y_med if y_med > 0 else False

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

    # Convert markdown bold to HTML bold for safe rendering
    rec_text_html = _escape_html(rec_text).replace("**", "<b>", 1).replace("**", "</b>", 1)
    st.markdown(
        f"""
        <div style="background:rgba(15, 23, 42, 0.9); border:1px solid rgba(99, 102, 241, 0.3); border-radius:12px; padding:18px 22px; margin-top:10px;">
            <div style="font-size:0.8rem; text-transform:uppercase; color:#818CF8; font-weight:700;">Status Diagnostik Akun Anda</div>
            <div style="font-size:1.15rem; font-weight:700; color:#FFFFFF; margin:4px 0 8px 0;">{_escape_html(quadrant_name)}</div>
            <p style="margin:0; font-size:0.9rem; color:#CBD5E1; line-height:1.5;">{rec_text_html}</p>
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
    all_account_choices = ["All Accounts"] + [acc["handle"] for acc in accounts_data if not acc.get("not_found")]
    col_acc_filter, col_metric_filter = st.columns([2, 2])
    
    with col_acc_filter:
        selected_timing_acc = st.selectbox(
            "Pilih Profil untuk Dianalisis",
            all_account_choices,
            format_func=lambda x: "Semua Profil (Aggregated)" if x == "All Accounts" else f"@{x} " + ("(You)" if x == main_handle else ""),
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
    if peak_info.get("value", 0) > 0:
        callout_html = f"""
        <div style="display:flex; align-items:center; gap:16px; background:linear-gradient(90deg, rgba(245, 158, 11, 0.15) 0%, rgba(99, 102, 241, 0.1) 100%); border:1px solid rgba(245, 158, 11, 0.4); border-radius:12px; padding:16px 20px; margin:14px 0 20px 0;">
            <div style="font-size:28px;">⭐</div>
            <div>
                <div style="font-size:0.8rem; text-transform:uppercase; color:#FCD34D; font-weight:700;">Rekomendasi Waktu Posting Optimal</div>
                <div style="font-size:1.1rem; font-weight:700; color:#FFFFFF;">
                    Hari {_escape_html(peak_info['day'])}, Pukul {_escape_html(peak_info['hour_label'])}
                </div>
                <div style="font-size:0.85rem; color:#E2E8F0;">
                    Slot ini menghasilkan rata-rata tertinggi sebesar <b style="color:#FCD34D;">{format_number(peak_info['value'])} interaksi</b> per postingan!
                </div>
            </div>
        </div>
        """
    else:
        callout_html = f"""
        <div style="display:flex; align-items:center; gap:16px; background:rgba(30, 41, 59, 0.5); border:1px solid rgba(255, 255, 255, 0.1); border-radius:12px; padding:16px 20px; margin:14px 0 20px 0;">
            <div style="font-size:28px;">ℹ️</div>
            <div>
                <div style="font-size:0.8rem; text-transform:uppercase; color:#94A3B8; font-weight:700;">Data Waktu Posting</div>
                <div style="font-size:1.0rem; font-weight:600; color:#FFFFFF;">
                    Belum ada data interaksi postingan yang tersedia untuk profil terpilih.
                </div>
                <div style="font-size:0.85rem; color:#94A3B8;">
                    Data timing membutuhkan metrik likes/comments dari postingan yang berhasil di-scrape.
                </div>
            </div>
        </div>
        """
    st.markdown(callout_html, unsafe_allow_html=True)

    # Heatmap Plotly Chart
    chart_title = f"Heatmap Intensitas Interaksi ({_escape_html(selected_timing_acc)})" if selected_timing_acc != "All Accounts" else "Heatmap Intensitas Interaksi Seluruh Akun"
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
        else:
            st.info("Data format konten belum tersedia. Metrik post perlu berhasil di-scrape terlebih dahulu.")

    st.markdown("---")

    # 2. Top Performing Posts Leaderboard
    st.subheader("🏆 Top Performing Posts Leaderboard")
    
    col_f_acc, col_f_sort = st.columns([2, 2])
    with col_f_acc:
        filter_post_acc = st.selectbox(
            "Filter Berdasarkan Akun",
            ["All Profiles"] + [acc["handle"] for acc in accounts_data if not acc.get("not_found")],
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
    
    if not ranked_posts_df.empty and sort_by_metric in ranked_posts_df.columns:
        ranked_posts_df = ranked_posts_df.sort_values(by=sort_by_metric, ascending=False).head(9)
        
        # Display posts in a 3-column grid
        post_cols = st.columns(3)
        for idx, (_, post_row) in enumerate(ranked_posts_df.iterrows()):
            col_target = post_cols[idx % 3]
            with col_target:
                caption_text = _escape_html(post_row.get("caption", ""))
                if len(caption_text) > 170:
                    caption_text = caption_text[:170] + "..."

                is_main_post = post_row.get("is_main", False)
                safe_account = _escape_html(post_row.get("account", ""))
                handle_badge = f"<span class='badge-pill badge-primary'>@{safe_account}</span>" if is_main_post else f"<span class='badge-pill' style='background:rgba(255,255,255,0.1); color:#CBD5E1;'>@{safe_account}</span>"
                
                post_date_display = _escape_html(
                    post_row.get("date") or (str(post_row.get("timestamp", ""))[:10] if post_row.get("timestamp") else "-")
                )
                content_type = post_row.get("content_type", "Post")
                fmt_badge = "📑 Carousel" if "Carousel" in content_type else ("📹 Reels" if "Reel" in content_type else "🖼️ Single")

                post_acc = post_row.get("account", "account")
                fallback_card = _generate_dynamic_account_card(post_acc)
                raw_thumb = post_row.get("thumbnail_url") or fallback_card
                
                # Validate URLs for security
                safe_thumb = raw_thumb if _is_safe_url(raw_thumb) else fallback_card
                safe_fallback = fallback_card if _is_safe_url(fallback_card) else ""
                
                post_url = post_row.get("post_url", "#")
                safe_post_url = post_url if _is_safe_url(post_url) else "#"

                is_estimated = post_row.get("is_estimated", False)
                estimation_badge_html = f"<div style='font-size:0.65rem; color:#F59E0B; margin-top:4px;'>⚠️ Metrik tidak tersedia</div>" if is_estimated else ""

                card_html = (
                    f'<div class="post-card">'
                    f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">'
                    f'<div style="display:flex; align-items:center; gap:6px;">'
                    f'{handle_badge}'
                    f'<span style="font-size:0.7rem; color:#A5B4FC; background:rgba(99,102,241,0.18); border:1px solid rgba(99,102,241,0.35); padding:2px 7px; border-radius:10px; font-weight:600;">{fmt_badge}</span>'
                    f'</div>'
                    f'<span style="font-size:0.75rem; color:#94A3B8;">{post_date_display}</span>'
                    f'</div>'
                    f'<img src="{safe_thumb}" referrerpolicy="no-referrer" onerror="this.onerror=null; this.src=\'{safe_fallback}\';" style="width:100%; height:165px; object-fit:cover; border-radius:8px; margin-bottom:10px;" />'
                    f'<div style="font-size:0.83rem; color:#E2E8F0; line-height:1.45; margin-bottom:12px; min-height:56px;">{caption_text}</div>'
                    f'<div style="display:flex; justify-content:space-between; align-items:center; font-size:0.8rem; background:rgba(30,41,59,0.55); padding:8px 10px; border-radius:8px;">'
                    f'<span>❤️ <b>{format_number(post_row["likes"])}</b></span>'
                    f'<span>💬 <b>{format_number(post_row["comments"])}</b></span>'
                    f'<span>🔁 <b>{format_number(post_row["shares"])}</b></span>'
                    f'<span style="color:#10B981; font-weight:700;">⚡ {post_row["post_er"]:.2f}%</span>'
                    f'</div>'
                    f'{estimation_badge_html}'
                    f'<div style="margin-top:10px; text-align:right;">'
                    f'<a href="{safe_post_url}" target="_blank" style="font-size:0.78rem; color:#818CF8; text-decoration:none; font-weight:600;">Lihat Postingan Asli ↗</a>'
                    f'</div>'
                    f'</div>'
                )

                if hasattr(st, "html"):
                    st.html(card_html)
                else:
                    st.markdown(card_html, unsafe_allow_html=True)
    else:
        st.info("Tidak ada data postingan yang cocok dengan kriteria filter.")

    st.markdown("---")

    # 3. Hashtag & Keyword Intelligence
    st.subheader("🏷️ Hashtag & Keyword Intelligence")
    st.caption("Analisis topik dan tagar yang ditemukan dalam caption postingan yang berhasil di-scrape.")

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
            st.info("Belum ada hashtag terdeteksi pada caption postingan yang di-scrape.")

    st.markdown("---")

    # 4. WordCloud Keyword & Topic Exploration
    st.subheader("☁️ WordCloud Topic & Keyword Visualizer")
    st.caption("Visualisasi frekuensi kata kunci dan topik dari caption postingan serta tagar yang digunakan.")

    col_wc_mode, col_wc_acc, col_wc_theme = st.columns([2, 2, 2])
    with col_wc_mode:
        wc_mode = st.radio(
            "Sumber Kata WordCloud",
            ["Kata Kunci Caption", "Tagar (#Hashtag)"],
            horizontal=True,
            key="wc_mode_select",
        )
    with col_wc_acc:
        wc_account = st.selectbox(
            "Filter Akun",
            ["All Profiles"] + [acc["handle"] for acc in accounts_data if not acc.get("not_found")],
            key="wc_account_filter",
        )
    with col_wc_theme:
        wc_colormap = st.selectbox(
            "Palet Warna",
            ["coolwarm", "plasma", "viridis", "mako", "Spectral", "Blues"],
            index=0,
            key="wc_colormap_select",
        )

    wc_mode_val = "hashtag" if "Hashtag" in wc_mode else "caption"
    frequencies = generate_wordcloud_frequencies(
        posts_df=posts_df,
        target_account=wc_account,
        mode=wc_mode_val,
        max_words=100,
    )

    if frequencies:
        fig_wc = create_wordcloud_figure(frequencies, colormap=wc_colormap, background_color="#0B1120")
        st.pyplot(fig_wc, use_container_width=True)

        # Show Top Keywords / Hashtags chip pills below WordCloud
        top_words = list(frequencies.items())[:12]
        chips_html = "".join([
            f"<span style='display:inline-block; background:rgba(99,102,241,0.18); border:1px solid rgba(99,102,241,0.35); color:#E0E7FF; padding:4px 10px; border-radius:12px; margin:3px 4px; font-size:0.78rem;'><b>{word}</b>: {count}x</span>"
            for word, count in top_words
        ])
        st.markdown(
            f"<div style='margin-top:10px; text-align:center;'>{chips_html}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("Belum ada data kata kunci atau tagar yang cukup dari postingan yang di-scrape untuk menghasilkan WordCloud.")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align:center; font-size:0.82rem; color:#64748B; padding:10px 0 20px 0;">
        ⚡ <b>SocialIQ Benchmarking System</b> — Social Intelligence • Built with Python & Streamlit • by <a href="https://threads.net/@itsamilitarysecret" target="_blank" style="color:#818CF8; text-decoration:none; font-weight:600;">threads.net/@itsamilitarysecret</a> • <a href="https://saweria.co/itsamilitarysecret" target="_blank" style="color:#F59E0B; text-decoration:none; font-weight:600;">☕ Traktir Kopi</a>
    </div>
    """,
    unsafe_allow_html=True,
)

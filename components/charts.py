"""
Plotly visualization builders for social media benchmarking.
Features 4-Quadrant Scatter, 7x24 Timing Heatmap, Format Performance Bar,
Hashtag Intelligence Leaderboard, and Follower Growth Chart.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.helpers import format_number, format_percent


# Theme Color Constants
COLOR_MAIN = "#6366F1"      # Indigo Violet for User's Brand
COLOR_ACCENT1 = "#06B6D4"   # Cyan
COLOR_ACCENT2 = "#10B981"   # Emerald
COLOR_ACCENT3 = "#F59E0B"   # Amber
COLOR_ACCENT4 = "#EC4899"   # Rose
COLOR_MUTED = "#64748B"     # Slate Gray
COLOR_GRID = "rgba(255, 255, 255, 0.08)"
COLOR_TEXT = "#E2E8F0"

PALETTE = [COLOR_MAIN, COLOR_ACCENT1, COLOR_ACCENT2, COLOR_ACCENT3, COLOR_ACCENT4, "#8B5CF6", "#F97316"]


def _empty_figure(message: str = "Data tidak tersedia", height: int = 350) -> go.Figure:
    """Create a styled empty figure with a message."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=16, color="#94A3B8"),
    )
    fig.update_layout(
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=height,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


def create_quadrant_scatter(comparison_df: pd.DataFrame, main_account: str) -> go.Figure:
    """
    Create 4-Quadrant Scatter Plot:
    X-axis: Posts per Day
    Y-axis: Engagement Rate (%)
    Bubble Size: Followers
    Divided by median lines into 4 strategic quadrants.
    """
    df = comparison_df.copy()
    if df.empty:
        return _empty_figure("Tidak ada data untuk quadrant plot")

    # Filter out accounts with 0 posts/day and 0 ER for meaningful quadrant
    plot_df = df[(df["Posts/Day"] > 0) | (df["ER (%)"] > 0)].copy()
    if plot_df.empty:
        return _empty_figure("Belum ada data posting untuk membuat quadrant plot")

    # Calculate median benchmarks
    x_med = float(plot_df["Posts/Day"].median()) if not plot_df["Posts/Day"].empty else 1.0
    y_med = float(plot_df["ER (%)"].median()) if not plot_df["ER (%)"].empty else 2.0

    # Ensure minimum range for quadrant visualization
    x_min = max(0, plot_df["Posts/Day"].min() * 0.7)
    x_max = plot_df["Posts/Day"].max() * 1.3
    y_min = max(0, plot_df["ER (%)"].min() * 0.7)
    y_max = plot_df["ER (%)"].max() * 1.35

    if x_max <= x_min:
        x_max = x_min + 2.0
    if y_max <= y_min:
        y_max = y_min + 3.0

    # Bubble sizing reference
    max_followers = max(1, plot_df["Followers"].max())
    plot_df["bubble_size"] = np.sqrt(plot_df["Followers"] / max_followers) * 38 + 14

    fig = go.Figure()

    # Add quadrant background tint / labels via annotations
    quadrant_annotations = [
        dict(
            x=x_min + (x_med - x_min) * 0.5,
            y=y_max * 0.94,
            text="✨ <b>HIGH EFFICIENCY</b><br><span style='font-size:10px;color:#94A3B8'>Low Frequency, High ER</span>",
            showarrow=False,
            font=dict(size=12, color="#10B981"),
            align="center",
            opacity=0.7,
        ),
        dict(
            x=x_med + (x_max - x_med) * 0.5,
            y=y_max * 0.94,
            text="🏆 <b>POWERHOUSES</b><br><span style='font-size:10px;color:#94A3B8'>High Frequency, High ER</span>",
            showarrow=False,
            font=dict(size=12, color="#6366F1"),
            align="center",
            opacity=0.7,
        ),
        dict(
            x=x_min + (x_med - x_min) * 0.5,
            y=y_min + (y_med - y_min) * 0.25,
            text="💤 <b>LOW IMPACT</b><br><span style='font-size:10px;color:#94A3B8'>Low Frequency, Low ER</span>",
            showarrow=False,
            font=dict(size=12, color="#94A3B8"),
            align="center",
            opacity=0.7,
        ),
        dict(
            x=x_med + (x_max - x_med) * 0.5,
            y=y_min + (y_med - y_min) * 0.25,
            text="⚠️ <b>SPAMMING / FATIGUE</b><br><span style='font-size:10px;color:#94A3B8'>High Frequency, Low ER</span>",
            showarrow=False,
            font=dict(size=12, color="#F59E0B"),
            align="center",
            opacity=0.7,
        ),
    ]

    # Plot each account bubble — use enumerate for consistent sequential indexing
    for seq_idx, (_, row) in enumerate(plot_df.iterrows()):
        is_main = bool(row["Is Main"])
        color = COLOR_MAIN if is_main else PALETTE[(seq_idx + 1) % len(PALETTE)]
        border_color = "#FFFFFF" if is_main else "rgba(255,255,255,0.4)"
        border_width = 2.5 if is_main else 1.5

        hover_text = (
            f"<b>{row['Profile']}</b><br>"
            f"Followers: <b>{format_number(row['Followers'])}</b><br>"
            f"Avg ER: <b>{row['ER (%)']:.2f}%</b><br>"
            f"Posts/Day: <b>{row['Posts/Day']:.2f}</b> ({row['Total Posts']} total)<br>"
            f"Avg Likes: <b>{format_number(row['Avg Likes'])}</b><br>"
            f"PPI Score: <b>{row['PPI']} / 100</b>"
        )

        fig.add_trace(
            go.Scatter(
                x=[row["Posts/Day"]],
                y=[row["ER (%)"]],
                mode="markers+text",
                name=row["Profile"],
                text=[f"  @{row['Handle']}"],
                textposition="middle right",
                textfont=dict(
                    size=12,
                    color="#FFFFFF" if is_main else "#CBD5E1",
                    family="Inter, sans-serif"
                ),
                marker=dict(
                    size=[row["bubble_size"]],
                    color=color,
                    opacity=0.85 if is_main else 0.70,
                    line=dict(color=border_color, width=border_width),
                ),
                hoverinfo="text",
                hovertext=[hover_text],
            )
        )

    # Median lines
    fig.add_vline(
        x=x_med,
        line_width=1.5,
        line_dash="dash",
        line_color="rgba(255, 255, 255, 0.25)",
        annotation_text=f"Median Freq: {x_med:.2f}/day",
        annotation_position="bottom right",
        annotation_font=dict(size=10, color="#94A3B8"),
    )
    fig.add_hline(
        y=y_med,
        line_width=1.5,
        line_dash="dash",
        line_color="rgba(255, 255, 255, 0.25)",
        annotation_text=f"Median ER: {y_med:.2f}%",
        annotation_position="top left",
        annotation_font=dict(size=10, color="#94A3B8"),
    )

    fig.update_layout(
        title=dict(
            text="<b>Efficiency & Quadrant Matrix</b> (Engagement Rate vs. Posting Frequency)",
            font=dict(size=16, color="#F8FAFC"),
        ),
        xaxis=dict(
            title="Posting Frequency (Posts per Day)",
            range=[x_min, x_max],
            gridcolor=COLOR_GRID,
            zeroline=False,
            color=COLOR_TEXT,
        ),
        yaxis=dict(
            title="Average Engagement Rate (%)",
            range=[y_min, y_max],
            gridcolor=COLOR_GRID,
            zeroline=False,
            color=COLOR_TEXT,
        ),
        annotations=quadrant_annotations,
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.28,
            xanchor="center",
            x=0.5,
            font=dict(color=COLOR_TEXT, size=11),
        ),
        margin=dict(l=50, r=40, t=60, b=80),
        height=520,
    )

    return fig


def create_timing_heatmap(
    heatmap_df: pd.DataFrame,
    peak_info: Dict[str, Any],
    title: str = "Best Time to Post Heatmap (7 Hari x 24 Jam)",
) -> go.Figure:
    """
    Create 7 Days x 24 Hours interactive heatmap with highlight on peak best slot.
    """
    if heatmap_df.empty:
        return _empty_figure("Tidak ada data timing untuk heatmap")

    days = heatmap_df.index.tolist()
    hours = [f"{h:02d}:00" for h in heatmap_df.columns]
    z_values = heatmap_df.values

    fig = go.Figure(
        data=go.Heatmap(
            z=z_values,
            x=hours,
            y=days,
            colorscale=[
                [0.0, "#0F172A"],
                [0.2, "#1E293B"],
                [0.4, "#312E81"],
                [0.7, "#6366F1"],
                [0.9, "#EC4899"],
                [1.0, "#F59E0B"],
            ],
            colorbar=dict(
                title=dict(text="Avg Interactions", font=dict(color=COLOR_TEXT, size=11)),
                tickfont=dict(color=COLOR_TEXT, size=10),
            ),
            hoverongaps=False,
            hovertemplate="<b>%{y} pukul %{x}</b><br>Rata-rata Interaksi: <b>%{z:,.0f}</b><extra></extra>",
        )
    )

    # Highlight peak slot if valid
    peak_day = peak_info.get("day", "")
    peak_hr = peak_info.get("hour", 0)
    peak_val = peak_info.get("value", 0)

    annotations = []
    if peak_day in days and peak_val > 0:
        annotations.append(
            dict(
                x=f"{peak_hr:02d}:00",
                y=peak_day,
                text="⭐ Best Slot",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor="#F59E0B",
                ax=0,
                ay=-35,
                bgcolor="#1E293B",
                bordercolor="#F59E0B",
                borderwidth=1,
                borderpad=4,
                font=dict(color="#FCD34D", size=11, family="Inter, sans-serif"),
            )
        )

    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=16, color="#F8FAFC")),
        xaxis=dict(
            title="Waktu Posting (Jam)",
            color=COLOR_TEXT,
            tickmode="linear",
            tickangle=-45,
            gridcolor=COLOR_GRID,
        ),
        yaxis=dict(
            title="Hari",
            color=COLOR_TEXT,
            autorange="reversed", # Senin at top
            gridcolor=COLOR_GRID,
        ),
        annotations=annotations,
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=60, r=40, t=60, b=60),
        height=450,
    )

    return fig


def create_format_performance_bar(format_df: pd.DataFrame) -> go.Figure:
    """
    Create grouped bar chart comparing performance across content formats.
    """
    if format_df.empty:
        return _empty_figure("Belum ada data format konten. Metrik post belum tersedia dari scraping.", height=380)

    fig = go.Figure()

    colors = ["#6366F1", "#06B6D4", "#10B981", "#F59E0B", "#EC4899"]

    fig.add_trace(
        go.Bar(
            name="Avg Interactions",
            x=format_df["content_type"],
            y=format_df["avg_interactions"],
            marker=dict(
                color=colors[: len(format_df)],
                line=dict(color="rgba(255,255,255,0.2)", width=1),
            ),
            text=[format_number(v) for v in format_df["avg_interactions"]],
            textposition="auto",
            textfont=dict(color="#FFFFFF", size=12),
            hovertemplate="<b>%{x}</b><br>Avg Interactions: %{y:,.0f}<extra></extra>",
        )
    )

    # Add secondary line for Avg ER (%)
    fig.add_trace(
        go.Scatter(
            name="Avg ER (%)",
            x=format_df["content_type"],
            y=format_df["avg_er"],
            yaxis="y2",
            mode="lines+markers+text",
            text=[f"{v:.2f}%" for v in format_df["avg_er"]],
            textposition="top center",
            textfont=dict(color="#F59E0B", size=11),
            line=dict(color="#F59E0B", width=2.5),
            marker=dict(size=8, color="#F59E0B"),
            hovertemplate="<b>%{x}</b><br>Avg ER: %{y:.2f}%<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(
            text="<b>Performance by Content Format</b> (Interactions & Engagement Rate)",
            font=dict(size=15, color="#F8FAFC"),
        ),
        xaxis=dict(title="Content Format", color=COLOR_TEXT, gridcolor=COLOR_GRID),
        yaxis=dict(title="Average Interactions", color=COLOR_TEXT, gridcolor=COLOR_GRID),
        yaxis2=dict(
            title="Average ER (%)",
            color="#F59E0B",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5,
            font=dict(color=COLOR_TEXT),
        ),
        margin=dict(l=50, r=50, t=60, b=60),
        height=380,
    )

    return fig


def create_hashtag_bar(hashtag_df: pd.DataFrame) -> go.Figure:
    """
    Create horizontal bar chart of top hashtags sorted by engagement.
    """
    if hashtag_df.empty:
        return _empty_figure("Belum ada hashtag terdeteksi dari caption postingan.", height=400)

    # Reverse order so highest engagement is at top
    df_sorted = hashtag_df.sort_values(by="avg_interactions", ascending=True)

    fig = go.Figure(
        go.Bar(
            x=df_sorted["avg_interactions"],
            y=df_sorted["hashtag"],
            orientation="h",
            marker=dict(
                color=df_sorted["avg_interactions"],
                colorscale="Viridis",
                line=dict(color="rgba(255,255,255,0.2)", width=1),
            ),
            text=[f" {format_number(v)} (ER {er:.2f}%)" for v, er in zip(df_sorted["avg_interactions"], df_sorted["avg_er"])],
            textposition="auto",
            textfont=dict(color="#FFFFFF", size=11),
            hovertemplate="<b>%{y}</b><br>Avg Interactions: %{x:,.0f}<br>Count: %{customdata[0]}<br>Avg ER: %{customdata[1]:.2f}%<extra></extra>",
            customdata=df_sorted[["count", "avg_er"]].values,
        )
    )

    fig.update_layout(
        title=dict(
            text="<b>Top Performing Hashtags & Topics</b> (by Average Interactions)",
            font=dict(size=15, color="#F8FAFC"),
        ),
        xaxis=dict(title="Average Interactions", color=COLOR_TEXT, gridcolor=COLOR_GRID),
        yaxis=dict(color=COLOR_TEXT, gridcolor=COLOR_GRID),
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=100, r=40, t=50, b=50),
        height=400,
    )

    return fig


def create_follower_growth_chart(all_accounts_data: List[Dict[str, Any]]) -> go.Figure:
    """
    Create multi-line follower growth trajectory over the analyzed period.
    """
    fig = go.Figure()
    has_data = False

    for idx, acc in enumerate(all_accounts_data):
        history = acc.get("historical_followers", [])
        if not history:
            continue
        
        dates = [h["date"] for h in history]
        followers = [h["followers"] for h in history]
        is_main = acc.get("is_main", False)
        
        color = COLOR_MAIN if is_main else PALETTE[(idx + 1) % len(PALETTE)]
        width = 3.5 if is_main else 1.8
        has_data = True

        fig.add_trace(
            go.Scatter(
                x=dates,
                y=followers,
                mode="lines+markers",
                name=f"@{acc['handle']}" + (" (You)" if is_main else ""),
                line=dict(color=color, width=width),
                marker=dict(size=5 if is_main else 3),
                hovertemplate=f"<b>@{acc['handle']}</b><br>Tanggal: %{{x}}<br>Followers: %{{y:,.0f}}<extra></extra>",
            )
        )

    if not has_data:
        return _empty_figure("Tidak ada data follower untuk ditampilkan")

    fig.update_layout(
        title=dict(
            text="<b>Follower Growth Trajectory</b>",
            font=dict(size=15, color="#F8FAFC"),
        ),
        xaxis=dict(title="Date", color=COLOR_TEXT, gridcolor=COLOR_GRID),
        yaxis=dict(
            title="Followers",
            color=COLOR_TEXT,
            gridcolor=COLOR_GRID,
            tickformat=",.0f",
        ),
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="center",
            x=0.5,
            font=dict(color=COLOR_TEXT),
        ),
        margin=dict(l=60, r=40, t=50, b=70),
        height=350,
    )

    return fig


def create_wordcloud_figure(
    frequencies: Dict[str, int],
    colormap: str = "coolwarm",
    background_color: str = "#0B1120",
    width: int = 900,
    height: int = 420,
):
    """
    Generates a matplotlib Figure containing a beautifully rendered WordCloud.
    Matches the dark aesthetic of the application.
    """
    import matplotlib.pyplot as plt
    try:
        from wordcloud import WordCloud
    except ImportError:
        fig, ax = plt.subplots(figsize=(width / 100, height / 100), facecolor=background_color)
        ax.text(0.5, 0.5, "Library wordcloud belum terpasang", color="#94A3B8", ha="center", va="center")
        ax.axis("off")
        return fig

    if not frequencies:
        fig, ax = plt.subplots(figsize=(width / 100, height / 100), facecolor=background_color)
        ax.text(0.5, 0.5, "Belum ada kata kunci / tagar yang terdeteksi untuk WordCloud", color="#94A3B8", ha="center", va="center", fontsize=12)
        ax.axis("off")
        return fig

    wc = WordCloud(
        width=width,
        height=height,
        background_color=background_color,
        colormap=colormap,
        prefer_horizontal=0.85,
        max_words=100,
        min_font_size=10,
        max_font_size=75,
        random_state=42,
        collocations=False,
    ).generate_from_frequencies(frequencies)

    fig, ax = plt.subplots(figsize=(width / 100, height / 100), facecolor=background_color, dpi=120)
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    plt.tight_layout(pad=0)
    return fig


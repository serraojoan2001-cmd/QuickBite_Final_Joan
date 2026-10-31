"""
ui.py — shared look & feel for every page: colours, CSS, KPI cards, chart styling, insight box,
and the cached loader that trains everything once per server start.
"""
from __future__ import annotations

import inspect

import streamlit as st

from core import build_artifacts

# ---- palette ----------------------------------------------------------------
SEG_COLORS = {"Budget students": "#00B8A9", "At-risk families": "#FF5D5D", "Premium foodies": "#7C4DFF"}
OUTCOME_COLORS = {"Churned": "#EF476F", "Reordered": "#06D6A0"}
ACCENT = ["#FF6B35", "#7C4DFF", "#06D6A0", "#FFB703", "#118AB2", "#EF476F"]
INK = "#1F2937"

CSS = """
<style>
.block-container, div[data-testid="stMainBlockContainer"] {padding-top: 4.5rem !important; padding-bottom: 2rem; max-width: 1280px;}
section[data-testid="stSidebar"] {background: linear-gradient(180deg, #FFF1E6 0%, #F1EAFF 100%);}
.brand {font-size: 1.35rem; font-weight: 800; color: #FF6B35; margin: .2rem 0 .1rem 0;}
.brand-s {font-size: .8rem; color: #6B7280; margin-bottom: .6rem;}
.hero {color: #fff; padding: 1.1rem 1.5rem; border-radius: 18px; margin-bottom: 1.1rem;
       box-shadow: 0 6px 18px rgba(124,77,255,.25);}
.hero-t {font-size: 1.8rem; font-weight: 800; line-height: 1.2;}
.hero-s {font-size: .95rem; opacity: .95; margin-top: .2rem;}
.kpi {color: #fff; border-radius: 16px; padding: .85rem 1.05rem; box-shadow: 0 4px 12px rgba(0,0,0,.12);}
.kpi .l {font-size: .72rem; letter-spacing: .06em; text-transform: uppercase; opacity: .92; font-weight: 600;}
.kpi .v {font-size: 2rem; font-weight: 800; line-height: 1.15;}
.kpi .s {font-size: .8rem; opacity: .95;}
.insights {background: #FFF8E1; border-left: 7px solid #FFB703; border-radius: 14px;
           padding: .9rem 1.3rem; margin-top: 1.4rem; color: #1F2937;}
.insights, .insights * {color: #1F2937;}
.insights h4 {margin: 0 0 .4rem 0; font-size: 1.05rem;}
.insights ul {margin: 0; padding-left: 1.2rem;}
.insights li {margin-bottom: .3rem;}
.chip {display: inline-block; padding: .4rem .95rem; border-radius: 999px; margin: .15rem .2rem .15rem 0;
       font-weight: 700; color: #fff; font-size: .95rem;}
.segcard {border-radius: 18px; padding: 1rem 1.3rem; color: #fff; box-shadow: 0 6px 16px rgba(0,0,0,.15);}
.segcard .l {font-size: .75rem; letter-spacing: .06em; text-transform: uppercase; opacity: .92;}
.segcard .v {font-size: 2rem; font-weight: 800;}
.fact {background: #fff; border-radius: 16px; padding: .9rem 1.1rem 1rem 1.1rem; color: #1F2937;
        box-shadow: 0 4px 14px rgba(0,0,0,.10); height: 100%;}
.fact, .fact * {color: #1F2937;}
.fact-h {font-size: 1.15rem; font-weight: 800; margin-bottom: .1rem;}
.fact-s {font-size: .8rem; color: #6B7280 !important; margin-bottom: .45rem;}
.fact ul {list-style: none; margin: 0; padding: 0;}
.fact li {font-size: .88rem; padding: .22rem 0; border-bottom: 1px dashed #E5E7EB;}
.fact li:last-child {border-bottom: 0;}
.section {font-size: 1.35rem; font-weight: 800; margin: 1.6rem 0 .2rem 0; line-height: 1.35; color: #FF6B35;}
.section .sec-t {background: linear-gradient(90deg,#FF6B35,#7C4DFF); -webkit-background-clip: text;
                 background-clip: text; -webkit-text-fill-color: transparent; padding-bottom: .1em;}
.chart-title {font-weight: 700; font-size: .98rem; color: #1F2937; line-height: 1.3; margin: .5rem 0 .1rem 0;}
.pill {display: inline-block; padding: .12rem .6rem; border-radius: 999px; font-size: .75rem; font-weight: 700; color: #fff;}
.section-s {color: #6B7280; font-size: .88rem; margin-bottom: .7rem;}
.tag {display: inline-block; padding: .2rem .7rem; border-radius: 8px; background: #FFE8D6; color: #B4470A;
      font-weight: 700; font-size: .78rem; margin-bottom: .5rem;}
</style>
"""


@st.cache_resource(show_spinner="Training the QuickBite models (about 15 seconds, once per start-up)…")
def get_artifacts() -> dict:
    return build_artifacts()


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str, icon: str = "", colors: tuple[str, str] = ("#FF6B35", "#7C4DFF")) -> None:
    st.markdown(
        f'<div class="hero" style="background:linear-gradient(120deg,{colors[0]},{colors[1]})">'
        f'<div class="hero-t">{icon} {title}</div><div class="hero-s">{subtitle}</div></div>',
        unsafe_allow_html=True)


def kpi_row(items: list[tuple[str, str, str, str]]) -> None:
    """items = [(label, value, sub-text, background colour), ...]"""
    cols = st.columns(len(items))
    for col, (label, value, sub, color) in zip(cols, items):
        col.markdown(
            f'<div class="kpi" style="background:{color}"><div class="l">{label}</div>'
            f'<div class="v">{value}</div><div class="s">{sub}</div></div>', unsafe_allow_html=True)


def chips(labels: list[str], colors: list[str] | None = None) -> None:
    colors = colors or ACCENT
    html = "".join(f'<span class="chip" style="background:{colors[i % len(colors)]}">{t}</span>'
                   for i, t in enumerate(labels))
    st.markdown(html, unsafe_allow_html=True)


def insights(bullets: list[str], title: str = "💡 Key insights") -> None:
    items = "".join(f"<li>{b}</li>" for b in bullets)
    st.markdown(f'<div class="insights"><h4>{title}</h4><ul>{items}</ul></div>', unsafe_allow_html=True)


def style(fig, title: str, xtitle: str | None = None, ytitle: str | None = None,
          height: int = 340, legend: bool = True, wrap: int = 0, side: int = 10):
    """Consistent, fully labelled Plotly look.

    The chart title is stored in the figure's `meta` and drawn as HTML above the chart by show(), so it can
    never be clipped by the chart's own margins. The legend sits above the plot, clear of the axis titles.
    (`wrap` is kept only so older calls keep working.)"""
    n_entries = sum(1 for t in fig.data if t.showlegend is not False)
    legend_room = (36 if n_entries <= 3 else 60) if legend else 8       # 4+ entries may wrap to two rows
    fig.update_layout(
        template="plotly_white", height=height, showlegend=legend, title=None, meta={"title": title},
        margin=dict(l=side, r=side, t=legend_room + 8, b=10), font=dict(color=INK),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, title_text=""))
    fig.update_xaxes(automargin=True, title_standoff=8)
    fig.update_yaxes(automargin=True, title_standoff=8)
    if xtitle:
        fig.update_xaxes(title_text=xtitle)
    if ytitle:
        fig.update_yaxes(title_text=ytitle)
    return fig


def section(title: str, subtitle: str = "") -> None:
    """Section heading. A leading emoji is kept outside the gradient text so it renders normally."""
    icon, _, text = title.partition(" ")
    if not text or any(ch.isalnum() for ch in icon):
        icon, text = "", title
    st.markdown(f'<div class="section">{icon + " " if icon else ""}<span class="sec-t">{text}</span></div>'
                f'<div class="section-s">{subtitle}</div>', unsafe_allow_html=True)


_HAS_WIDTH = "width" in inspect.signature(st.plotly_chart).parameters


def show(fig, key: str | None = None) -> None:
    """Render a Plotly figure full-width, with its title (from style()) as HTML above it."""
    meta = fig.layout.meta
    title = meta.get("title") if isinstance(meta, dict) else None
    if title:
        st.markdown(f'<div class="chart-title">{title}</div>', unsafe_allow_html=True)
    if _HAS_WIDTH:
        st.plotly_chart(fig, width="stretch", theme=None, key=key)
    else:
        st.plotly_chart(fig, use_container_width=True, theme=None, key=key)


_TABLE_HAS_WIDTH = "width" in inspect.signature(st.dataframe).parameters


def table(df, **kwargs) -> None:
    """st.dataframe, full width, without index (works on old and new Streamlit versions)."""
    if _TABLE_HAS_WIDTH:
        st.dataframe(df, width="stretch", hide_index=True, **kwargs)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True, **kwargs)

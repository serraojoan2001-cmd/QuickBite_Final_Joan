"""Page 3 — Basket Combos (market-basket / Apriori association rules)."""
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from core import SEGMENTS, pairs_excluding, staple_evidence
from ui import SEG_COLORS, get_artifacts, hero, insights, kpi_row, section, show, style, table

A = get_artifacts()
P, share, bsize = A["pairs"], A["item_share"], A["basket_size"]
nice = lambda s: s.replace("_", " ")

hero("Basket Combos", "Which menu items are ordered together — overall and inside each segment", "🛒", ("#FF6B35", "#FFB703"))

kpi_row([("All baskets", f"{A['n_baskets']:,}", f"{A['orders']['item'].nunique()} menu items", "#F26B21")] +
        [(f"{seg} · basket size", f"{bsize[seg]:.2f}", "average items per order", SEG_COLORS[seg]) for seg in SEGMENTS])
st.write("")

sel = st.radio("Show combos for", ["All diners"] + SEGMENTS, horizontal=True)
all_items = sorted(A["bk"].columns)
hide = st.multiselect("Hide items from the combos (e.g. a habit add-on like cola)", all_items, format_func=nice,
                      help="Items are removed from every basket but no basket is deleted, so all other figures stay comparable.")
pairs = pairs_excluding(A, sel, hide) if hide else P[sel].copy()
color = "#F26B21" if sel == "All diners" else SEG_COLORS[sel]

c1, c2 = st.columns([3, 2])
with c1:
    fig = go.Figure(go.Bar(
        y=[nice(r) for r in pairs["rule"]], x=pairs["lift"], orientation="h", marker_color=color,
        text=[f"lift {l:.1f} · {c:.0%} of the time" for l, c in zip(pairs["lift"], pairs["confidence"])],
        textposition="outside", cliponaxis=False,
        hovertemplate="%{y}<br>lift %{x:.2f}<extra></extra>"))
    fig.add_vline(x=1, line_dash="dash", line_color="#6B7280", annotation_text="lift 1 = no association",
                  annotation_position="bottom right")
    fig.update_xaxes(range=[0, max(pairs["lift"].max(), 1.5) * 1.6])
    fig.update_yaxes(autorange="reversed")
    show(style(fig, f"Strongest item combos — {sel}", "Lift (× more often than by chance)",
               "If a diner orders …  →  they also order …", 380, legend=False))
with c2:
    t = pairs.assign(Rule=pairs["rule"].map(nice), Support=pairs["support"] * 100,
                     Confidence=pairs["confidence"] * 100)[["Rule", "Support", "Confidence", "lift"]]
    table(t, column_config={
        "Support": st.column_config.NumberColumn("Support (% of baskets)", format="%.1f"),
        "Confidence": st.column_config.ProgressColumn("Confidence (%)", min_value=0, max_value=100, format="%.0f%%"),
        "lift": st.column_config.NumberColumn("Lift", format="%.2f")})
    st.caption("Confidence = share of baskets with the first item that also contain the second.")

# ---- menu mix heatmap ---------------------------------------------------------------
order = share.max(axis=1).sort_values(ascending=False).index
z = share.loc[order] * 100
fig = go.Figure(go.Heatmap(
    z=z.values, x=SEGMENTS, y=[nice(i) for i in order],
    text=[[f"{v:.0f}%" if v >= 0.5 else "" for v in row] for row in z.values], texttemplate="%{text}",
    colorscale=[[0, "#F5F3FF"], [0.5, "#B197FC"], [1, "#6741D9"]],
    colorbar=dict(title="% of segment's items"), hovertemplate="%{y} in %{x}: %{z:.1f}%<extra></extra>"))
fig.update_yaxes(autorange="reversed")
show(style(fig, "Menu mix: how each segment's items split across the menu", "Segment", "Menu item", 520, legend=False, wrap=90))

# ---- staple check: is cola distorting the picture? -----------------------------------
ev = staple_evidence(A, "cola")
home = ev["home"]
section("🥤 Staple check: cola", "Is a very common item biasing the combos? Test: does it depend on what else is in the basket?")
s1, s2 = st.columns(2)
with s1:
    keys = list(ev["attach"])
    fig = go.Figure(go.Bar(x=[nice(k) if k != "Any other item" else "all baskets" for k in keys],
                           y=[v * 100 for v in ev["attach"].values()],
                           marker_color=["#00B8A9"] * (len(keys) - 1) + ["#9CA3AF"],
                           text=[f"{v:.0%}" for v in ev["attach"].values()], textposition="outside", cliponaxis=False))
    fig.update_yaxes(range=[0, 118])
    show(style(fig, f"Cola attach rate in {home} baskets, by what else is ordered", "Basket contains …",
               "Baskets that also have cola (%)", 340, legend=False))
with s2:
    segs = SEGMENTS
    fig = go.Figure()
    fig.add_bar(name="With cola", x=segs, y=[ev["size_with"][g] for g in segs], marker_color="#FF6B35",
                text=[f"{ev['size_with'][g]:.2f}" for g in segs], textposition="outside", cliponaxis=False)
    fig.add_bar(name="Cola removed", x=segs, y=[ev["size_without"][g] for g in segs], marker_color="#7C4DFF",
                text=[f"{ev['size_without'][g]:.2f}" for g in segs], textposition="outside", cliponaxis=False)
    fig.update_layout(barmode="group"); fig.update_yaxes(range=[0, 3.5])
    show(style(fig, "Average basket size with and without cola", "Segment", "Items per basket", 340))
fam_with = pairs_excluding(A, "At-risk families", [], 3)
fam_wo = pairs_excluding(A, "At-risk families", ["cola"], 3)
st.caption(f"Cola is in {ev['share_all']:.0%} of all baskets: {ev['share_seg'][home]:.0%} of {home}, "
           f"{ev['share_seg']['At-risk families']:.0%} of At-risk families, {ev['share_seg']['Premium foodies']:.0%} of Premium foodies.")

# ---- key insights --------------------------------------------------------------------
stu_items = set(share.index[share["Budget students"] > 0])
other_items = set(share.index[(share[["At-risk families", "Premium foodies"]] > 0).any(axis=1)])
shared = sorted(stu_items & other_items)
top3 = P["All diners"].head(3)
fam_top, pre_top = P["At-risk families"].head(2), P["Premium foodies"].head(2)
stu_best = P["Budget students"]["lift"].max()
insights([
    "<b>Strongest overall combos:</b> " + "; ".join(f"{nice(r.rule)} (lift {r.lift:.1f})" for r in top3.itertuples())
    + " — promote each pair together.",
    f"<b>Overall lifts are inflated by segment mix:</b> menus barely overlap — Budget students order only "
    f"{len(stu_items)} items and share just {', '.join(nice(s) for s in shared)} with other segments.",
    "<b>Families:</b> " + "; ".join(f"{nice(r.rule)} (lift {r.lift:.1f})" for r in fam_top.itertuples())
    + " → build a 'family feast' bundle.",
    "<b>Premium foodies:</b> " + "; ".join(f"{nice(r.rule)} (lift {r.lift:.1f})" for r in pre_top.itertuples())
    + " → curated 'dinner for two' sets.",
    f"<b>Cola is a habit, not a pairing:</b> it is in {ev['attach_base']:.0%} of {home} baskets whatever else is ordered "
    f"(lift ≈ 1.0 with every item), so it adds volume but no signal. Hide it and the other combos do not move — "
    f"the real exception is families, where cola + garlic bread is a genuine pairing.",
    f"<b>Budget students:</b> best lift is only {stu_best:.2f} — they buy the same cheap staples regardless of basket, "
    f"so a fixed-price combo deal beats cross-selling.",
])

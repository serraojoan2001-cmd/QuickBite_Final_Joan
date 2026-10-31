"""Page 2 — Diner Segments (K-Means clustering)."""
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core import FEATURES, NICE, RADAR_LABELS, SEGMENTS
from ui import SEG_COLORS, get_artifacts, hero, insights, kpi_row, show, style, table

A = get_artifacts()
d, S, kt = A["diners"], A["segment_summary"], A["k_table"]
k_best = int(A["k_final"])

hero("Diner Segments", "Three behaviour-based groups found with K-Means clustering", "👥", ("#00B8A9", "#7C4DFF"))

kpi_row([(seg, f"{int(S.loc[seg, 'diners'])} diners",
          f"{S.loc[seg, 'diners'] / len(d):.0%} of base · {S.loc[seg, 'orders_per_month']:.1f} orders/mo · "
          f"{S.loc[seg, 'avg_order_value']:.0f} AED/order", SEG_COLORS[seg]) for seg in SEGMENTS])
st.write("")

# ---- row 1: how many segments? -----------------------------------------------------
c1, c2 = st.columns(2)
with c1:
    fig = go.Figure(go.Scatter(x=kt["k"], y=kt["inertia"], mode="lines+markers", name="Inertia",
                               line=dict(color="#FF6B35", width=3), marker=dict(size=8)))
    pick = kt[kt["k"] == k_best].iloc[0]
    fig.add_trace(go.Scatter(x=[k_best], y=[pick["inertia"]], mode="markers+text", name=f"Chosen k = {k_best}",
                             marker=dict(size=16, color="#EF476F", line=dict(width=2, color="white")),
                             text=[f"k = {k_best}"], textposition="top right"))
    fig.update_xaxes(dtick=1)
    show(style(fig, f"Elbow method: inertia by number of segments", "Number of segments (k)",
               "Inertia (within-segment spread)", 340))
with c2:
    fig = go.Figure(go.Scatter(x=kt["k"], y=kt["silhouette"], mode="lines+markers", name="Silhouette score",
                               line=dict(color="#00B8A9", width=3), marker=dict(size=8)))
    fig.add_trace(go.Scatter(x=[k_best], y=[pick["silhouette"]], mode="markers+text", name=f"Chosen k = {k_best}",
                             marker=dict(size=16, color="#EF476F", line=dict(width=2, color="white")),
                             text=[f"{pick['silhouette']:.3f}"], textposition="top right"))
    fig.update_xaxes(dtick=1)
    show(style(fig, f"Silhouette score by number of segments", "Number of segments (k)",
               "Silhouette score (higher = better separated)", 340))

# ---- row 2: who are they? ------------------------------------------------------------
c3, c4 = st.columns(2)
with c3:
    rng = A["feature_ranges"]
    theta = [RADAR_LABELS[f] for f in FEATURES]
    fig = go.Figure()
    for seg in SEGMENTS:
        r = [(S.loc[seg, f] - rng.loc["min", f]) / (rng.loc["max", f] - rng.loc["min", f]) for f in FEATURES]
        fig.add_trace(go.Scatterpolar(r=r + r[:1], theta=theta + theta[:1], name=seg, fill="toself", opacity=0.55,
                                      line=dict(color=SEG_COLORS[seg], width=2)))
    fig.update_layout(polar=dict(radialaxis=dict(range=[0, 1], showticklabels=False)))
    show(style(fig, "Segment profile (centre = lowest diner, outer ring = highest diner)", height=420, side=70)
         .update_layout(margin=dict(t=110, b=30), legend=dict(y=1.16)))
with c4:
    fig = px.scatter(d, x="orders_per_month", y="avg_order_value", color="segment", hover_name="diner_id",
                     color_discrete_map=SEG_COLORS, category_orders={"segment": SEGMENTS}, opacity=0.8,
                     hover_data={"segment": False, "age": True, "reordered": True})
    fig.update_traces(marker=dict(size=8, line=dict(width=0.5, color="white")))
    show(style(fig, "Every diner: order frequency vs order value", "Orders per month",
               "Average order value (AED)", 400))

# ---- profile table -------------------------------------------------------------------
tbl = S.reset_index().rename(columns={"segment": "Segment"})
tbl["Reorder rate"] = tbl["reorder_rate"] * 100
tbl["Discount rate"] = tbl["discount_rate"] * 100
table(tbl[["Segment", "diners", "age", "orders_per_month", "avg_order_value", "avg_items_per_order",
           "days_since_last_order", "Discount rate", "Reorder rate"]],
      column_config={
          "diners": st.column_config.NumberColumn("Diners", format="%d"),
          "age": st.column_config.NumberColumn("Avg age", format="%.0f"),
          "orders_per_month": st.column_config.NumberColumn("Orders / month", format="%.1f"),
          "avg_order_value": st.column_config.NumberColumn("Avg order (AED)", format="%.0f"),
          "avg_items_per_order": st.column_config.NumberColumn("Items / order", format="%.1f"),
          "days_since_last_order": st.column_config.NumberColumn("Days since last order", format="%.0f"),
          "Discount rate": st.column_config.NumberColumn("Discount rate (% of orders)", format="%.0f%%"),
          "Reorder rate": st.column_config.ProgressColumn("Reorder rate", min_value=0, max_value=100, format="%.0f%%"),
      })

# ---- key insights --------------------------------------------------------------------
k2, k4 = kt.loc[kt["k"] == 2, "silhouette"].iloc[0], kt.loc[kt["k"] == 4, "silhouette"].iloc[0]
i2, i3 = kt.loc[kt["k"] == 2, "inertia"].iloc[0], kt.loc[kt["k"] == 3, "inertia"].iloc[0]
stu, fam, pre = (S.loc[s] for s in SEGMENTS)
insights([
    f"<b>3 segments is the right number:</b> silhouette peaks at {pick['silhouette']:.3f} for k = 3 "
    f"(k = 2: {k2:.3f}, k = 4: {k4:.3f}) and inertia drops sharply from {i2:.0f} to {i3:.0f} before flattening.",
    f"<b>Budget students</b> — young (avg {stu['age']:.0f}), order {stu['orders_per_month']:.0f}× a month, small baskets "
    f"({stu['avg_order_value']:.0f} AED), {stu['discount_rate']:.0%} of orders discounted, {stu['reorder_rate']:.0%} reorder. Loyal but low margin.",
    f"<b>At-risk families</b> — order rarely ({fam['orders_per_month']:.1f}×/month) but big: {fam['avg_items_per_order']:.0f} items, "
    f"{fam['avg_order_value']:.0f} AED; {fam['days_since_last_order']:.0f} days since last order; only {fam['reorder_rate']:.0%} reorder.",
    f"<b>Premium foodies</b> — {pre['avg_order_value']:.0f} AED per order, almost no discounts ({pre['discount_rate']:.0%}), highest lifetime "
    f"spend ({pre['total_spend_mean']:.0f} AED) but only {pre['reorder_rate']:.0%} reorder.",
])

"""Page 1 — Business Snapshot (executive summary): every answer at a glance."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import SEGMENTS
from ui import OUTCOME_COLORS, SEG_COLORS, get_artifacts, hero, insights, kpi_row, section, show, style

A = get_artifacts()
d, S, M = A["diners"], A["segment_summary"], A["clf_metrics"]
SO = A["spend_by_outcome"]

hero("Business Snapshot", "Who our diners are, what they order together, and who is about to leave", "📊")

kpi_row([
    ("Diners analysed", f"{len(d)}", f"{A['n_baskets']:,} baskets · 17 menu items", "#F26B21"),
    ("Reorder rate", f"{d['reordered'].mean():.0%}", f"{1 - d['reordered'].mean():.0%} churned", "#0FA678"),
    ("Segments found", f"{A['k_final']}", "K-Means · best silhouette", "#7C4DFF"),
    ("Churn model accuracy", f"{M['accuracy']:.1%}", f"vs {M['baseline']:.1%} baseline", "#118AB2"),
])
st.write("")

# ---- row 1: who are they, who stays, where the money is --------------------------------
c1, c2, c3 = st.columns(3)
with c1:
    fig = go.Figure(go.Pie(labels=SEGMENTS, values=S["diners"], hole=0.55, sort=False,
                           marker=dict(colors=[SEG_COLORS[s] for s in SEGMENTS]),
                           textinfo="value+percent", hovertemplate="%{label}: %{value} diners<extra></extra>"))
    show(style(fig, "Diners per segment (count and share)", height=330))
with c2:
    fig = go.Figure(go.Bar(x=SEGMENTS, y=S["reorder_rate"] * 100,
                           marker_color=[SEG_COLORS[s] for s in SEGMENTS],
                           text=[f"{v:.0%}" for v in S["reorder_rate"]], textposition="outside", cliponaxis=False))
    fig.update_yaxes(range=[0, 115])
    show(style(fig, "Reorder rate by segment", "Segment", "Diners who reordered (%)", 330, legend=False))
with c3:
    fig = go.Figure()
    for outcome in ["Reordered", "Churned"]:
        fig.add_bar(name=outcome, x=SEGMENTS, y=SO[outcome] / 1000, marker_color=OUTCOME_COLORS[outcome],
                    text=[f"{v / 1000:.0f}k" for v in SO[outcome]], textposition="inside")
    fig.update_layout(barmode="stack")
    show(style(fig, "Lifetime spend by reorder outcome", "Segment", "Total spend (AED thousands)", 330))

# ---- row 2: what to promote, how good is the model -----------------------------------
c4, c5 = st.columns(2)
with c4:
    best = [A["pairs"][s].iloc[0] for s in SEGMENTS]
    fig = go.Figure(go.Bar(
        y=SEGMENTS, x=[b["lift"] for b in best], orientation="h",
        marker_color=[SEG_COLORS[s] for s in SEGMENTS],
        text=[f"{b['rule'].replace('_', ' ')}  (lift {b['lift']:.1f})" for b in best],
        textposition="outside", cliponaxis=False))
    fig.add_vline(x=1, line_dash="dash", line_color="#6B7280",
                  annotation_text="lift 1 = no association", annotation_position="bottom right")
    fig.update_xaxes(range=[0, max(b["lift"] for b in best) * 1.75])
    fig.update_yaxes(autorange="reversed")
    show(style(fig, "Strongest item combo per segment", "Lift (× more often than chance)", "Segment", 330, legend=False))
with c5:
    labels = ["Baseline<br>(always 'reordered')", "Model accuracy<br>(test set)",
              "Model accuracy<br>(5-fold average)", "Churners caught<br>(recall)"]
    vals = [M["baseline"], M["accuracy"], M["cv_mean"], M["churn_recall"]]
    fig = go.Figure(go.Bar(x=labels, y=[v * 100 for v in vals],
                           marker_color=["#9CA3AF", "#118AB2", "#4CC9F0", "#EF476F"],
                           text=[f"{v:.1%}" for v in vals], textposition="outside", cliponaxis=False))
    fig.update_yaxes(range=[0, 115])
    show(style(fig, "Churn model vs baseline", "Measure", "Percent (%)", 330, legend=False))

# ---- customer fact sheet: descriptive facts only (interpretation lives in "Key insights" below) -------------
section("🧠 Customer Fact Sheet — what to remember about our diners",
        "Plain facts from the data, kept separate from the insights below")

ICONS = {"Budget students": "🎓", "At-risk families": "👨‍👩‍👧", "Premium foodies": "🍣"}
total_spend = S["total_spend_sum"].sum()
for col, seg in zip(st.columns(3), SEGMENTS):
    r, best = S.loc[seg], A["pairs"][seg].iloc[0]
    favourites = ", ".join(i.replace("_", " ") for i in A["reco"][seg])
    col.markdown(
        f'''<div class="fact" style="border-top:8px solid {SEG_COLORS[seg]}">
        <div class="fact-h" style="color:{SEG_COLORS[seg]} !important">{ICONS[seg]} {seg}</div>
        <div class="fact-s">{int(r["diners"])} diners · {r["diners"] / len(d):.0%} of the base</div>
        <ul>
        <li><b>Age:</b> {r["age"]:.0f} on average</li>
        <li><b>Orders:</b> {r["orders_per_month"]:.1f} a month · {r["avg_items_per_order"]:.1f} items · {r["avg_order_value"]:.0f} AED each</li>
        <li><b>Last order:</b> {r["days_since_last_order"]:.0f} days ago on average</li>
        <li><b>Discounts:</b> used on {r["discount_rate"]:.0%} of orders</li>
        <li><b>Reorder rate:</b> {r["reorder_rate"]:.0%}</li>
        <li><b>Lifetime spend:</b> {r["total_spend_mean"]:.0f} AED each · {r["total_spend_sum"] / 1000:.0f}k AED in total ({r["total_spend_sum"] / total_spend:.0%} of all spend)</li>
        <li><b>Favourite items:</b> {favourites}</li>
        <li><b>Best combo:</b> {best["rule"].replace("_", " ")} (lift {best["lift"]:.1f})</li>
        </ul></div>''', unsafe_allow_html=True)
st.write("")

# early-warning signals: reorder rate when a signal is present vs absent
signals = {
    "More than 20 days since last order": d["days_since_last_order"] > 20,
    "5 or fewer orders a month": d["orders_per_month"] <= 5,
    "Average order of 150+ AED": d["avg_order_value"] >= 150,
    "Age 35 or older": d["age"] >= 35,
    "Discount on 50%+ of orders": d["discount_rate"] >= 0.5,
}
f1, f2 = st.columns([3, 2])
with f1:
    names = list(signals)
    present = [d.loc[m, "reordered"].mean() * 100 for m in signals.values()]
    absent = [d.loc[~m, "reordered"].mean() * 100 for m in signals.values()]
    counts = [int(m.sum()) for m in signals.values()]
    fig = go.Figure()
    fig.add_bar(y=names, x=present, name="Signal present", orientation="h", marker_color="#FF6B35",
                text=[f"{v:.0f}%  (n={n})" for v, n in zip(present, counts)], textposition="outside", cliponaxis=False)
    fig.add_bar(y=names, x=absent, name="Signal absent", orientation="h", marker_color="#9CA3AF",
                text=[f"{v:.0f}%" for v in absent], textposition="outside", cliponaxis=False)
    fig.update_xaxes(range=[0, 125])
    fig.update_yaxes(autorange="reversed")
    show(style(fig, "Reorder rate when a warning signal is present vs absent", "Diners who reordered (%)",
               "Diner signal", 400, wrap=80))
with f2:
    bins = [-1, 5, 10, 15, 20, 1000]
    labels = ["0–5", "6–10", "11–15", "16–20", "21+"]
    g = d.groupby(pd.cut(d["days_since_last_order"], bins=bins, labels=labels), observed=True)["reordered"].agg(["mean", "count"])
    fig = go.Figure(go.Bar(x=list(g.index.astype(str)), y=g["mean"] * 100,
                           marker_color=["#06D6A0", "#7ED957", "#FFD166", "#FF9F43", "#EF476F"][: len(g)],
                           text=[f"{m:.0%}" for m in g["mean"]], textposition="outside", cliponaxis=False,
                           customdata=g["count"], hovertemplate="%{x} days: %{y:.0f}% reordered (n=%{customdata})<extra></extra>"))
    fig.update_yaxes(range=[0, 118])
    show(style(fig, "Reorder rate falls as days since last order grow", "Days since last order",
               "Diners who reordered (%)", 400, legend=False, wrap=52))
st.caption("Thresholds are round numbers chosen for readability. Signals overlap with segments (most students are "
           "under 25, most families are over 35), so use the Churn Radar page for the combined risk.")

# ---- key insights --------------------------------------------------------------------
fam, stu, pre = S.loc["At-risk families"], S.loc["Budget students"], S.loc["Premium foodies"]
lost_share = SO.loc["At-risk families", "Churned"] / SO.loc["At-risk families"].sum()
fam_pair, pre_pair = A["pairs"]["At-risk families"].iloc[0], A["pairs"]["Premium foodies"].iloc[0]
stu_best = A["pairs"]["Budget students"]["lift"].max()
insights([
    f"<b>Focus on At-risk families:</b> {fam['avg_order_value']:.0f} AED per order and ~{fam['avg_items_per_order']:.0f} items, "
    f"but only {fam['reorder_rate']:.0%} reorder — {lost_share:.0%} of their lifetime spend "
    f"({SO.loc['At-risk families', 'Churned'] / 1000:.0f}k AED) sits with diners who did not come back.",
    f"<b>Promote bundles:</b> {fam_pair['rule'].replace('_', ' ')} (lift {fam_pair['lift']:.1f}) for families and "
    f"{pre_pair['rule'].replace('_', ' ')} (lift {pre_pair['lift']:.1f}) for premium foodies. Students have no real combos "
    f"(best lift {stu_best:.2f}) — use a fixed-price combo deal instead.",
    f"<b>Protect Premium foodies:</b> highest average lifetime spend ({pre['total_spend_mean']:.0f} AED) but only "
    f"{pre['reorder_rate']:.0%} reorder — a good target for retention offers.",
    f"<b>Skip retention spend on Budget students:</b> {stu['reorder_rate']:.0%} reorder, low value "
    f"({stu['avg_order_value']:.0f} AED per order, heavy discounting).",
    f"<b>Use the churn model weekly:</b> it catches {M['churn_caught']} of {M['churn_caught'] + M['churn_missed']} churners "
    f"({M['churn_recall']:.0%}) at {M['accuracy']:.1%} accuracy vs a {M['baseline']:.1%} baseline — contact flagged diners "
    f"before they lapse.",
])

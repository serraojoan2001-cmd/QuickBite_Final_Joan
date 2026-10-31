"""Page 4 — Churn Radar (classification: who will reorder?)."""
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core import NICE, SEGMENTS
from ui import OUTCOME_COLORS, SEG_COLORS, get_artifacts, hero, insights, kpi_row, show, style

A = get_artifacts()
M, imp, thr, d = A["clf_metrics"], A["clf_importance"], A["threshold_table"], A["diners"]
caught, missed, false_alarm, loyal_ok = M["churn_caught"], M["churn_missed"], M["false_alarms"], M["loyal_ok"]
n_churn = caught + missed

hero("Churn Radar", "A random-forest model that predicts which diners will reorder — and which are about to leave",
     "🎯", ("#EF476F", "#7C4DFF"))

kpi_row([
    ("Accuracy (test set)", f"{M['accuracy']:.1%}", f"{M['n_test']} unseen diners", "#118AB2"),
    ("Baseline", f"{M['baseline']:.1%}", "always guess 'reordered'", "#6B7280"),
    ("Churners caught", f"{caught} of {n_churn}", f"{M['churn_recall']:.0%} recall", "#EF476F"),
    ("5-fold accuracy", f"{M['cv_mean']:.1%}", "average over 5 splits", "#0FA678"),
])
st.write("")

# ---- row 1 ---------------------------------------------------------------------------
c1, c2, c3 = st.columns(3)
with c1:
    labels = ["Baseline", "Model<br>(test set)", "Model<br>(5-fold)"]
    vals = [M["baseline"], M["accuracy"], M["cv_mean"]]
    fig = go.Figure(go.Bar(x=labels, y=[v * 100 for v in vals], marker_color=["#9CA3AF", "#118AB2", "#4CC9F0"],
                           text=[f"{v:.1%}" for v in vals], textposition="outside", cliponaxis=False))
    fig.update_yaxes(range=[0, 115])
    show(style(fig, "Accuracy: model vs baseline", "Version", "Accuracy (%)", 360, legend=False))
with c2:
    z = [[caught, missed], [false_alarm, loyal_ok]]
    fig = go.Figure(go.Heatmap(
        z=z, x=["Predicted: churn", "Predicted: reorder"], y=["Actually churned", "Actually reordered"],
        text=[[f"{caught}<br>churners caught", f"{missed}<br>churners missed"],
              [f"{false_alarm}<br>loyal flagged", f"{loyal_ok}<br>loyal kept"]],
        texttemplate="%{text}", colorscale=[[0, "#F5F3FF"], [1, "#6741D9"]], showscale=False,
        hovertemplate="%{y} · %{x}: %{z} diners<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    show(style(fig, "Confusion matrix (test set, diners)", "Model prediction", "What really happened", 360, legend=False))
with c3:
    s = imp.sort_values()
    fig = go.Figure(go.Bar(y=[NICE[i] for i in s.index], x=s.values * 100, orientation="h",
                           marker_color="#FF6B35",
                           text=[f"{v:.0%}" for v in s.values], textposition="outside", cliponaxis=False))
    fig.update_xaxes(range=[0, s.max() * 100 * 1.25])
    show(style(fig, "What drives reordering", "Importance (% of model decisions)", "Diner feature", 360, legend=False))

# ---- row 2 ---------------------------------------------------------------------------
c4, c5 = st.columns(2)
with c4:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=thr["threshold"], y=thr["churners_caught"] * 100, mode="lines+markers",
                             name="Churners caught", line=dict(color="#EF476F", width=3)))
    fig.add_trace(go.Scatter(x=thr["threshold"], y=thr["loyal_flagged"] * 100, mode="lines+markers",
                             name="Loyal diners wrongly flagged", line=dict(color="#118AB2", width=3)))
    fig.add_vline(x=0.5, line_dash="dash", line_color="#6B7280", annotation_text="default cut-off 0.5")
    show(style(fig, "Cost trade-off: how strict should the alert be?", "Churn-risk cut-off (flag diner if risk ≥ cut-off)",
               "Share of diners (%)", 380))
with c5:
    plot = d.assign(p=A["oof_reorder"] * 100)
    fig = px.box(plot, x="segment", y="p", color="segment", color_discrete_map=SEG_COLORS,
                 category_orders={"segment": SEGMENTS}, points="all")
    fig.update_traces(marker=dict(size=4, opacity=0.5))
    show(style(fig, "Predicted reorder likelihood by segment", "Segment",
               "Predicted reorder likelihood (%, cross-validated)", 380, legend=False))

# ---- key insights --------------------------------------------------------------------
corr = A["reorder_corr"]
top = imp.index[:3]
t5 = thr.loc[thr["threshold"] == 0.3].iloc[0]
insights([
    f"<b>Beats the baseline by {100 * (M['accuracy'] - M['baseline']):.0f} points:</b> {M['accuracy']:.1%} vs {M['baseline']:.1%} "
    f"on {M['n_test']} unseen diners ({M['cv_mean']:.1%} on average across 5 folds).",
    f"<b>Missing a churner costs more than a false alarm:</b> a lost diner is gone; a false alarm only wastes a small offer. "
    f"The model catches {caught} of {n_churn} churners ({missed} missed) and wrongly flags {false_alarm} of "
    f"{false_alarm + loyal_ok} loyal diners.",
    "<b>Top drivers:</b> " + ", ".join(f"{NICE[f].lower()} (higher → {'more' if corr[f] > 0 else 'less'} likely to reorder)"
                                        for f in top) + ".",
    f"<b>Tune the alert:</b> a cut-off of 0.3 flags {t5['churners_caught']:.0%} of churners but also {t5['loyal_flagged']:.0%} "
    f"of loyal diners; raise it when offers are expensive.",
    f"<b>Weekly routine:</b> score diners, send win-back offers to those flagged — most urgent in the "
    f"{min(SEGMENTS, key=lambda s: d.loc[d['segment'] == s, 'reordered'].mean())} segment.",
])

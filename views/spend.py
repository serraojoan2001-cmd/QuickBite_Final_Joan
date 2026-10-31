"""Page 5 — Spend Forecast (regression: predicting a diner's total spend). Bonus analysis."""
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from core import NICE, SEGMENTS
from ui import SEG_COLORS, get_artifacts, hero, insights, kpi_row, show, style

A = get_artifacts()
R, d = A["reg"], A["diners"]
imp, corr = R["importance"], R["corr"]

hero("Spend Forecast", "Regression model that estimates a diner's total spend (AED) from their behaviour",
     "💰", ("#118AB2", "#06D6A0"))
st.markdown('<span class="tag">BONUS ANALYSIS · extension to the brief, not one of its four tasks</span>',
            unsafe_allow_html=True)

kpi_row([
    ("Model used", R["best"], "best of 3 tested", "#118AB2"),
    ("R² (5-fold)", f"{R['r2']:.2f}", "share of spend variation explained", "#7C4DFF"),
    ("Typical error", f"±{R['mae']:.0f} AED", "mean absolute error", "#F26B21"),
    ("Average diner spend", f"{d['total_spend'].mean():.0f} AED", f"range {d['total_spend'].min():.0f}–{d['total_spend'].max():.0f}", "#0FA678"),
])
st.write("")

c1, c2, c3 = st.columns(3)
with c1:
    names = list(R["cv_r2"])
    vals = [R["cv_r2"][n] for n in names]
    fig = go.Figure(go.Bar(x=[n.replace(" ", "<br>") for n in names], y=vals,
                           marker_color=["#9CA3AF" if n != R["best"] else "#118AB2" for n in names],
                           text=[f"{v:.2f}" for v in vals], textposition="outside", cliponaxis=False))
    fig.update_yaxes(range=[0, 1.1])
    show(style(fig, "Model comparison (best highlighted)", "Model", "R² (5-fold average, higher is better)", 380, legend=False))
with c2:
    plot = d.assign(pred=R["oof_pred"])
    fig = px.scatter(plot, x="total_spend", y="pred", color="segment", color_discrete_map=SEG_COLORS,
                     category_orders={"segment": SEGMENTS}, hover_name="diner_id", opacity=0.8)
    lo, hi = float(d["total_spend"].min()), float(d["total_spend"].max())
    fig.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines", name="Perfect prediction",
                             line=dict(color="#1F2937", dash="dash")))
    show(style(fig, "Actual vs predicted total spend", "Actual total spend (AED)", "Predicted total spend (AED)", 380))
with c3:
    s = imp.sort_values()
    fig = go.Figure(go.Bar(y=[NICE[i] for i in s.index], x=s.values * 100, orientation="h", marker_color="#FFB703",
                           text=[f"{v:.0%}" for v in s.values], textposition="outside", cliponaxis=False))
    fig.update_xaxes(range=[0, s.max() * 100 * 1.25])
    show(style(fig, "What drives total spend", "Importance (% of model decisions)", "Diner feature", 380, legend=False))

# ---- key insights --------------------------------------------------------------------
top = list(imp.index[:3])
lin_r2 = R["cv_r2"]["Linear regression"]
insights([
    f"<b>Spend is predictable:</b> {R['best'].lower()} explains {R['r2']:.0%} of the variation in total spend, "
    f"typically within ±{R['mae']:.0f} AED (average spend is {d['total_spend'].mean():.0f} AED).",
    "<b>Three behaviours drive spend:</b> " + ", ".join(NICE[f].lower() for f in top)
    + f" together account for {imp[top].sum():.0%} of the model's decisions.",
    f"<b>Discounts and lifetime spend move in opposite directions:</b> correlation {corr['discount_rate']:+.2f} between discount "
    f"rate and total spend — heavily discounted diners spend less in total (an association, not proof of cause).",
    f"<b>Not a straight line:</b> linear regression reaches only R² {lin_r2:.2f} vs {R['cv_r2'][R['best']]:.2f}, so spend "
    f"depends on combinations of behaviours.",
    "<b>Use it to rank diners by value</b> and decide where a retention offer is worth its cost.",
])

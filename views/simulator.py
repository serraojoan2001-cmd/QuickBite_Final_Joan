"""Page 6 — Diner Simulator (live demo): type in a diner, see segment, reorder likelihood and recommendations."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import (CLF_FEATURES, FEATURES, NICE, RADAR_LABELS, SEGMENTS, analyse_diner, search_diners, search_fields,
                  segment_distances, sweep_feature)
from ui import SEG_COLORS, chips, get_artifacts, hero, insights, section, show, style

A = get_artifacts()
d = A["diners"].set_index("diner_id")
nice = lambda s: s.replace("_", " ")

hero("Diner Simulator", "Type in a diner and instantly see their segment, reorder likelihood and what to offer",
     "🔮", ("#7C4DFF", "#FF6B35"))

# ---- state: inputs live in session_state so presets / ID lookup can fill them -------------------------
DEFAULT = dict(age=28, orders_per_month=8, avg_order_value=90.0, avg_items_per_order=3,
               days_since_last_order=10, discount_rate=0.30, total_spend=800.0)
PRESETS = {
    "🎓 Frequent student": dict(age=21, orders_per_month=14, avg_order_value=40.0, avg_items_per_order=2,
                               days_since_last_order=4, discount_rate=0.60, total_spend=500.0),
    "👨‍👩‍👧 Lapsed family": dict(age=40, orders_per_month=3, avg_order_value=175.0, avg_items_per_order=6,
                              days_since_last_order=25, discount_rate=0.30, total_spend=600.0),
    "🍣 Premium regular": dict(age=33, orders_per_month=9, avg_order_value=100.0, avg_items_per_order=3,
                              days_since_last_order=8, discount_rate=0.10, total_spend=900.0),
}
for k, v in DEFAULT.items():
    st.session_state.setdefault(f"sim_{k}", v)
st.session_state.setdefault("sim_msg", "")


def apply_profile(profile: dict, msg: str = "") -> None:
    for k, v in profile.items():
        st.session_state[f"sim_{k}"] = v
    st.session_state["sim_msg"] = msg


def load_diner(diner_id: str) -> None:
    row = d.loc[diner_id]
    profile = dict(age=int(row["age"]), orders_per_month=int(row["orders_per_month"]),
                   avg_order_value=float(row["avg_order_value"]), avg_items_per_order=int(row["avg_items_per_order"]),
                   days_since_last_order=int(row["days_since_last_order"]), discount_rate=float(row["discount_rate"]),
                   total_spend=float(row["total_spend"]))
    outcome = "reordered" if row["reordered"] == 1 else "did not reorder (churned)"
    apply_profile(profile, f"Loaded {diner_id} — in the data this diner {outcome}.")


def load_picked() -> None:
    pick = st.session_state.get("sim_pick")
    if pick:
        load_diner(pick.split(" · ")[0])


# ---- layout: inputs left, live result right ---------------------------------------------------------
left, right = st.columns([1, 1.25], gap="large")

with left:
    st.markdown("#### 1 · Enter a diner")
    pc = st.columns(3)
    for col, (label, prof) in zip(pc, PRESETS.items()):
        col.button(label, on_click=apply_profile, args=(prof, f"Loaded preset: {label}"))
    with st.expander("🔎 Find an existing diner (search by ID, segment, status, items, or any extra column)"):
        st.text_input("Search", key="sim_q", placeholder="e.g. D1293, families, churned, miso soup"
                      + (" — or a name / email" if A["extra_cols"] else ""))
        f1, f2 = st.columns(2)
        f1.multiselect("Segment", SEGMENTS, key="sim_segf")
        f2.selectbox("Outcome", ["Any", "Reordered", "Churned"], key="sim_status")
        f3, f4 = st.columns(2)
        f3.slider("Age range", 8, 70, (8, 70), key="sim_agef")
        f4.slider("Days since last order", 0, 60, (0, 60), key="sim_daysf")
        f5 = st.multiselect("Has ordered any of", sorted(A["orders"]["item"].unique()), key="sim_itemf",
                            format_func=nice)
        hits = search_diners(A, st.session_state["sim_q"], st.session_state["sim_segf"], st.session_state["sim_status"],
                             st.session_state["sim_agef"], st.session_state["sim_daysf"], None, f5)
        st.caption(f"{len(hits)} diner(s) match" + (" — showing the first 50." if len(hits) > 50 else "."))
        labels = [f"{r.diner_id} · {r.segment} · {r.status} · age {r.age}" for r in hits.head(50).itertuples()]
        if labels:
            st.selectbox("Matches", labels, key="sim_pick")
            st.button("Load this diner", on_click=load_picked)
        st.caption("Searches every word you type across: " + ", ".join(search_fields(A)) + ".")
    if st.session_state["sim_msg"]:
        st.caption(st.session_state["sim_msg"])

    st.slider("Age", 8, 70, key="sim_age")
    st.slider("Orders per month", 1, 25, key="sim_orders_per_month")
    st.slider("Average order value (AED)", 15.0, 250.0, step=1.0, key="sim_avg_order_value")
    st.slider("Average items per order", 1, 10, key="sim_avg_items_per_order")
    st.slider("Days since last order", 0, 60, key="sim_days_since_last_order")
    st.slider("Discount usage rate", 0.0, 1.0, step=0.01, key="sim_discount_rate")
    st.number_input("Total spend so far (AED)", min_value=0.0, max_value=20000.0, step=50.0, key="sim_total_spend")

profile = {k: st.session_state[f"sim_{k}"] for k in DEFAULT}
res = analyse_diner(A, profile)
seg, p = res["segment"], res["p_reorder"]
color = SEG_COLORS[seg]

if p < 0.40:
    band, band_color, action = "At risk of churning", "#EF476F", "Send a win-back offer now"
elif p < 0.60:
    band, band_color, action = "Watch closely", "#FFB703", "Nudge with a bundle before they drift"
else:
    band, band_color, action = "Likely to reorder", "#06D6A0", "Keep warm — suggest a bundle to grow basket size"

with right:
    st.markdown("#### 2 · Live result")
    st.markdown(f'<div class="segcard" style="background:{color}"><div class="l">Diner segment</div>'
                f'<div class="v">{seg}</div></div>', unsafe_allow_html=True)
    st.caption("Assigned automatically from the five behaviour inputs (orders, order value, items, recency, discounts). "
               "Age and total spend do not change the segment, but they do change the reorder likelihood.")

    gauge = go.Figure(go.Indicator(
        mode="gauge+number", value=p * 100, number=dict(suffix="%", font=dict(size=46)),
        title=dict(text=f"<b>Reorder likelihood — {band}</b>", font=dict(size=15)),
        gauge=dict(axis=dict(range=[0, 100], ticksuffix="%"), bar=dict(color="#1F2937", thickness=0.28),
                   steps=[dict(range=[0, 40], color="#FFC2D1"), dict(range=[40, 60], color="#FFE8A3"),
                          dict(range=[60, 100], color="#A8F0D8")],
                   threshold=dict(line=dict(color=band_color, width=5), thickness=0.85, value=p * 100))))
    gauge.update_layout(height=310, margin=dict(l=55, r=55, t=75, b=50), paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#1F2937"))
    show(gauge)
    st.caption("Risk bands: red under 40% · amber 40–60% · green 60% and above")

    st.markdown(f"**Recommended items for {seg}** — most-ordered items, habit add-ons excluded")
    chips([nice(i) for i in res["items"]], ["#FF6B35", "#7C4DFF", "#00B8A9", "#FFB703", "#118AB2"])
    if res["staples"]:
        st.caption("Not worth recommending (already in nearly every basket): " + ", ".join(nice(i) for i in res["staples"]))
    if res["bundles"]:
        st.markdown("**Bundle to promote** — pairs ordered together far more than by chance")
        chips([f"{nice(b['antecedents'])} + {nice(b['consequents'])}  (lift {b['lift']:.1f})" for b in res["bundles"]],
              [color, color])
    else:
        st.markdown("**Bundle to promote** — no strong pairs in this segment; offer a fixed-price combo of the items above.")
    st.markdown(f'<div style="background:{band_color};color:#1F2937;border-radius:12px;padding:.6rem 1rem;'
                f'font-weight:700;margin-top:.6rem">➡ Suggested action: {action}</div>', unsafe_allow_html=True)

# ---- context charts -------------------------------------------------------------------------------------
c1, c2 = st.columns(2)
with c1:
    rng = A["feature_ranges"]
    S = A["segment_summary"]
    theta = [RADAR_LABELS[f] for f in FEATURES]
    norm = lambda f, v: min(max((v - rng.loc["min", f]) / (rng.loc["max", f] - rng.loc["min", f]), 0), 1)
    this = [norm(f, profile[f]) for f in FEATURES]
    avg = [norm(f, S.loc[seg, f]) for f in FEATURES]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=avg + avg[:1], theta=theta + theta[:1], name=f"{seg} average", fill="toself",
                                  opacity=0.45, line=dict(color=color, width=2)))
    fig.add_trace(go.Scatterpolar(r=this + this[:1], theta=theta + theta[:1], name="This diner",
                                  line=dict(color="#1F2937", width=3)))
    fig.update_layout(polar=dict(radialaxis=dict(range=[0, 1], showticklabels=False)))
    show(style(fig, "This diner vs segment average (centre = lowest diner, outer ring = highest diner)", height=420, side=70)
         .update_layout(margin=dict(t=110, b=30), legend=dict(y=1.16)))
with c2:
    dd = A["diners"]
    fig = go.Figure()
    for s in SEGMENTS:
        sub = dd[dd["segment"] == s]
        fig.add_trace(go.Scatter(x=sub["orders_per_month"], y=sub["avg_order_value"], mode="markers", name=s,
                                 marker=dict(color=SEG_COLORS[s], size=7, opacity=0.55)))
    fig.add_trace(go.Scatter(x=[profile["orders_per_month"]], y=[profile["avg_order_value"]], mode="markers",
                             name="This diner", marker=dict(symbol="star", size=22, color="#FFD60A",
                                                            line=dict(width=2, color="#1F2937"))))
    show(style(fig, "Where this diner sits among all diners", "Orders per month", "Average order value (AED)", 400))


# ---- why this segment? + what-if explorer ----------------------------------------------------------------
section("🔬 What-if explorer — how does each feature change the answer?",
        "Change one input at a time with everything else held at the values above")

e1, e2 = st.columns(2)
with e1:
    dist = segment_distances(A, profile)
    fig = go.Figure(go.Bar(y=SEGMENTS, x=dist.values, orientation="h",
                           marker_color=[SEG_COLORS[s] for s in SEGMENTS],
                           text=[f"{v:.2f}" + ("  ← assigned" if s == seg else "") for s, v in dist.items()],
                           textposition="outside", cliponaxis=False))
    fig.update_xaxes(range=[0, max(dist.max() * 1.35, 1)])
    fig.update_yaxes(autorange="reversed")
    show(style(fig, "Why this segment? Distance to each segment's centre", "Distance (lower = closer fit)",
               "Segment", 340, legend=False))
with e2:
    rows = []
    for f in CLF_FEATURES:
        sw = sweep_feature(A, profile, f)
        rows.append({"feature": NICE[f], "swing": (sw["p_reorder"].max() - sw["p_reorder"].min()) * 100,
                     "moves_segment": sw["segment"].nunique() > 1})
    tor = pd.DataFrame(rows).sort_values("swing")
    fig = go.Figure(go.Bar(
        y=tor["feature"], x=tor["swing"], orientation="h",
        marker_color=["#7C4DFF" if m else "#FF6B35" for m in tor["moves_segment"]],
        text=[f"{v:.0f} pts" + ("  · changes segment" if m else "") for v, m in zip(tor["swing"], tor["moves_segment"])],
        textposition="outside", cliponaxis=False))
    fig.update_xaxes(range=[0, tor["swing"].max() * 2.2])
    show(style(fig, "Which inputs move the reorder likelihood most? (full range of each input)",
               "Swing in reorder likelihood (percentage points)", "Input", 340, legend=False, wrap=44))
st.caption("Purple bars: moving that input across its range can also switch the diner into a different segment. "
           "Orange bars: it changes the reorder likelihood only.")

pick = st.selectbox("Explore one input in detail", CLF_FEATURES, format_func=lambda f: NICE[f],
                    index=CLF_FEATURES.index("age"), key="sim_explore")
sw = sweep_feature(A, profile, pick)
fig = go.Figure()
fig.add_trace(go.Scatter(x=sw["value"], y=sw["p_reorder"] * 100, mode="lines", name="Reorder likelihood",
                         line=dict(color="#9CA3AF", width=3), showlegend=False, hoverinfo="skip"))
for s in SEGMENTS:
    sub_ = sw[sw["segment"] == s]
    if len(sub_):
        fig.add_trace(go.Scatter(x=sub_["value"], y=sub_["p_reorder"] * 100, mode="markers", name=f"Segment: {s}",
                                 marker=dict(color=SEG_COLORS[s], size=9)))
fig.add_trace(go.Scatter(x=[profile[pick]], y=[p * 100], mode="markers", name="This diner now",
                         marker=dict(symbol="star", size=20, color="#FFD60A", line=dict(width=2, color="#1F2937"))))
fig.add_hrect(y0=0, y1=40, fillcolor="#FFC2D1", opacity=0.25, line_width=0)
fig.add_hrect(y0=60, y1=100, fillcolor="#A8F0D8", opacity=0.25, line_width=0)
fig.update_yaxes(range=[0, 100])
show(style(fig, f"Effect of {NICE[pick].lower()} on reorder likelihood and segment",
           NICE[pick], "Reorder likelihood (%)", 400, wrap=70))
seg_set = sw["segment"].unique().tolist()
if len(seg_set) == 1:
    st.caption(f"Across its whole range, {NICE[pick].lower()} never changes the segment (always {seg_set[0]}). "
               + ("It is not one of the five inputs used to assign segments." if pick in ("age", "total_spend") else
                  "The other inputs hold this diner firmly in that segment."))
else:
    st.caption(f"{NICE[pick]} can move this diner between segments: " + ", ".join(seg_set) + ".")

# ---- key insights ---------------------------------------------------------------------------------------
corr, imp = A["reorder_corr"], A["clf_importance"]
f1, f2 = imp.index[0], imp.index[1]
insights([
    f"<b>This diner:</b> {seg} · {p:.0%} reorder likelihood · {band.lower()} → {action.lower()}.",
    f"<b>What moves the score most:</b> {NICE[f1].lower()} and {NICE[f2].lower()} "
    f"(correlation with reordering {corr[f1]:+.2f} and {corr[f2]:+.2f}). Try changing them with the sliders.",
    "<b>Segment vs reorder:</b> the segment comes only from the five behaviour inputs; age and total spend never change it "
    "but still shift the reorder likelihood — use the What-if explorer to see by how much.",
    "<b>Recommendations</b> are the segment's five most-ordered items; bundles appear only when a pair's lift is 1.5 or higher.",
    "<b>Best use:</b> check a diner before a campaign — treat red as win-back, amber as nudge, green as upsell.",
])

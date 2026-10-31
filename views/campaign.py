"""Page 7 — Campaign Planner: promo bundles for under-exposed items, live basket upsell, and the 20% discount decision."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import SEGMENTS, bundle_candidates, campaign_shortlist, discount_scenario, suggest_addons
from ui import SEG_COLORS, get_artifacts, hero, insights, kpi_row, section, show, style, table

A = get_artifacts()
EXP = A["exposure"]
nice = lambda s: s.replace("_", " ")
EVID_COLORS = {"Strong pull": "#06D6A0", "Some pull": "#FFB703", "No pull": "#9CA3AF", "No history": "#C7D2FE"}

hero("Campaign Planner", "Which promo bundles to run, what to offer at the basket, and who deserves a 20% discount",
     "📣", ("#EF476F", "#FFB703"))

tab1, tab2, tab3 = st.tabs(["🎁 Promo bundles", "🛒 Basket upsell", "💸 20% discount decision"])

# =============================================================================================
with tab1:
    section("Pair rarely-ordered items with best-sellers", "Goal: more exposure for the menu's quiet items and new baskets, not just more cola")
    under = list(EXP.index[EXP["exposure"] == "Under-exposed"])
    k1, k2, k3 = st.columns(3)
    k1.metric("Under-exposed items", len(under), help="Bottom third of the menu by number of baskets")
    k2.metric("Items sold to only one segment", int((EXP["sold_to"] == 1).sum()), help="Most of the menu never reaches the other two segments")
    k3.metric("Median item share of baskets", f"{EXP['share_all'].median():.1%}")

    fig = go.Figure(go.Bar(
        y=[nice(i) for i in EXP.index], x=EXP["share_all"] * 100, orientation="h",
        marker_color=[{"Under-exposed": "#EF476F", "Mid": "#FFB703", "Best-seller": "#06D6A0"}[e] for e in EXP["exposure"]],
        text=[f"{v:.1%}" for v in EXP["share_all"]], textposition="outside", cliponaxis=False,
        customdata=EXP["exposure"], hovertemplate="%{y}: %{x:.1f}% of baskets (%{customdata})<extra></extra>"))
    fig.update_xaxes(range=[0, EXP["share_all"].max() * 100 * 1.18])
    show(style(fig, "Menu exposure: share of all baskets containing each item (red = under-exposed, green = best-seller)",
               "Baskets containing the item (%)", "Menu item", 520, legend=False))

    section("Build a bundle", "Pick the item to promote and the segment it should reach")
    c1, c2, c3 = st.columns([1.2, 1, 1])
    mode = c1.radio("Promote", ["An item already on the menu", "A new item (not in the data)"], key="cp_mode")
    seg = c2.selectbox("Target segment", SEGMENTS, key="cp_seg")
    take = c3.slider("Share of anchor baskets that take the offer", 0.02, 0.30, 0.10, 0.01, key="cp_take",
                     help="Assumption. 10% is a typical bundle take-up; adjust to your own history.")
    proxy = None
    if mode.startswith("An item"):
        opts = under + [i for i in EXP.index if i not in under]
        promo = st.selectbox("Item to promote", opts, index=opts.index("miso_soup") if "miso_soup" in opts else 0, format_func=nice, key="cp_item")
    else:
        n1, n2 = st.columns(2)
        promo = n1.text_input("New item name", "boba tea", key="cp_new").strip().lower().replace(" ", "_") or "new_item"
        proxy = n2.selectbox("Behaves most like (existing item used as the stand-in)", list(EXP.index), format_func=nice,
                             index=list(EXP.index).index("green_tea"), key="cp_proxy")
        st.info(f"**{nice(promo)}** has no sales history, so no real pairing can be proven. Its stand-in "
                f"**{nice(proxy)}** shows what similar items do in this segment. Treat the result as a hypothesis for an A/B test.")

    cand = bundle_candidates(A, seg, promo, proxy, take)
    if cand.empty:
        st.warning("No frequent items to attach to in this segment.")
    else:
        top = cand.iloc[0]
        proven = cand[cand["evidence"].isin(["Strong pull", "Some pull"])]
        if len(proven):
            b = proven.sort_values("est_new", ascending=False).iloc[0]
            st.success(f"**Recommended bundle: {nice(b['anchor'])} + {nice(promo)}** for {seg}. Past pull: lift {b['lift']:.1f}, "
                       f"{b['confidence']:.0%} of {nice(b['anchor'])} baskets already hold it. "
                       f"About **{b['est_new']:.0f} extra baskets** at a {take:.0%} take-up.")
        else:
            b = cand.sort_values("est_new", ascending=False).iloc[0]
            st.warning(f"**No proven pairing for {seg}.** The biggest opening is **{nice(b['anchor'])} + {nice(promo)}** "
                       f"({b['anchor_baskets']:,} baskets, ~{b['est_new']:.0f} extra at {take:.0%}), but it is untested here, so run it as a pilot.")
        fig = go.Figure()
        for ev, g in cand.groupby("evidence"):
            fig.add_bar(name=ev, y=[nice(a) for a in g["anchor"]], x=g["est_new"], orientation="h", marker_color=EVID_COLORS[ev],
                        text=[f"{v:.0f}" for v in g["est_new"]], textposition="outside", cliponaxis=False,
                        customdata=g[["lift", "confidence"]], hovertemplate="%{y}: ~%{x:.0f} new baskets<br>lift %{customdata[0]:.2f}<extra></extra>")
        fig.update_yaxes(autorange="reversed")
        fig.update_xaxes(range=[0, cand["est_new"].max() * 1.2])
        show(style(fig, f"Estimated new baskets for {nice(promo)} by anchor item in {seg} (colour = past evidence)",
                   "Estimated extra baskets", "Anchor (best-seller to attach to)", 120 + 48 * len(cand)))
        t = cand.assign(Anchor=cand["anchor"].map(nice), Share=cand["anchor_share"] * 100, Conf=cand["confidence"] * 100)
        table(t[["Anchor", "anchor_baskets", "together", "Conf", "lift", "evidence", "est_new"]], column_config={
            "anchor_baskets": st.column_config.NumberColumn("Anchor baskets", format="%d"),
            "together": st.column_config.NumberColumn("Already together", format="%d"),
            "Conf": st.column_config.NumberColumn("% of anchor baskets with promo item", format="%.0f"),
            "lift": st.column_config.NumberColumn("Lift", format="%.2f"),
            "evidence": st.column_config.TextColumn("Evidence"),
            "est_new": st.column_config.NumberColumn("Est. new baskets", format="%.0f")})
        st.caption("Lift ≥ 1.5 strong pull · 1.2–1.5 some pull · below 1.2 no pull · 'No history' = the pair never occurred (new to this segment). "
                   "Estimated new baskets = anchor baskets that do not yet hold the promo item × take-up.")

    section("Best proven bundle per segment", "Under-exposed items only; a pair must already show a lift of 1.2 or more")
    sl = campaign_shortlist(A, take)
    cols = st.columns(3)
    for col, (_, r) in zip(cols, sl.iterrows()):
        if r["promo"] is None or pd.isna(r["promo"]):
            col.markdown(f'<div class="fact" style="border-top:8px solid {SEG_COLORS[r["segment"]]}"><div class="fact-h">{r["segment"]}</div>'
                         f'<div class="fact-s">No under-exposed item sold to this segment</div><ul><li>Students only order 4 items, so there is nothing '
                         f'rare to push inside their menu. Use the cross-segment pilot below.</li></ul></div>', unsafe_allow_html=True)
        else:
            col.markdown(f'<div class="fact" style="border-top:8px solid {SEG_COLORS[r["segment"]]}"><div class="fact-h" '
                         f'style="color:{SEG_COLORS[r["segment"]]} !important">{r["segment"]}</div>'
                         f'<div class="fact-s">Bundle: {nice(r["anchor"])} + {nice(r["promo"])}</div><ul>'
                         f'<li><b>Lift:</b> {r["lift"]:.2f} ({r["evidence"].lower()})</li>'
                         f'<li><b>Anchor baskets without it:</b> {int(r["gap"])}</li>'
                         f'<li><b>Est. new baskets:</b> ~{r["est_new"]:.0f} at {take:.0%} take-up</li></ul></div>', unsafe_allow_html=True)

    insights([
        f"<b>Most of the menu is siloed:</b> {int((EXP['sold_to'] == 1).sum())} of {len(EXP)} items are bought by only one segment. "
        f"The quick win is pushing each segment's quiet items to the people already buying that segment's best-sellers.",
        "<b>Use proven pairs first:</b> miso soup + sushi / green tea (Premium) and garlic bread + dessert (Families) already show lift above 1.2, "
        "so a bundle is backed by behaviour rather than a guess.",
        "<b>New items (boba tea, etc.) need a pilot:</b> with no sales history the stand-in item gives a hypothesis, not proof. "
        "Offer it to half of the matching baskets and compare against the other half before rolling out.",
        "<b>Do not anchor on cola:</b> it sits in 90% of student baskets whatever else is ordered, so bundling with it only adds a free ride. "
        "Anchor on fries, burger or wrap for students.",
        "<b>Cross-segment pairing is untested:</b> students have never ordered miso soup. Treat it as an experiment, not a forecast.",
    ])

# =============================================================================================
with tab2:
    section("When a diner is ordering", "Pick their segment and what is already in the basket; get the next best offer")
    u1, u2 = st.columns(2)
    seg2 = u1.selectbox("Diner's segment", SEGMENTS, key="up_seg")
    menu2 = sorted(EXP.index[EXP[seg2] > 0], key=lambda i: -EXP.loc[i, seg2])
    default_basket = menu2[:1]
    basket = u1.multiselect("Already in the basket", menu2, default=default_basket, format_func=nice, key=f"up_basket_{seg2}")
    promos = u2.multiselect("Campaign items to push", list(EXP.index) + ["boba_tea"], default=[i for i in ["miso_soup", "garlic_bread"] if i in EXP.index][:2],
                            format_func=nice, key="up_promo")
    sa = suggest_addons(A, seg2, basket, promos)
    if len(basket) == 0 or sa.empty:
        st.info("Add at least one item to the basket to see suggestions.")
    else:
        natural = sa[(sa["type"] == "Natural") & (sa["confidence"] > 0)].head(1)
        camp = sa[sa["type"] == "Campaign"]
        k = st.columns(3)
        if len(natural):
            r = natural.iloc[0]
            k[0].markdown(f'<div class="kpi" style="background:#118AB2"><div class="l">Natural add-on</div><div class="v">{nice(r["item"])}</div>'
                          f'<div class="s">{r["confidence"]:.0%} of similar baskets include it</div></div>', unsafe_allow_html=True)
        if len(camp):
            r = camp.iloc[0]
            conf = "no history in this segment, pilot it" if pd.isna(r["confidence"]) else f"{r['confidence']:.0%} of similar baskets"
            k[1].markdown(f'<div class="kpi" style="background:#EF476F"><div class="l">Campaign offer</div><div class="v">{nice(r["item"])}</div>'
                          f'<div class="s">{conf}</div></div>', unsafe_allow_html=True)
        stp = sa[sa["type"] == "Staple"]
        if len(stp):
            k[2].markdown(f'<div class="kpi" style="background:#9CA3AF"><div class="l">Skip (habit add-on)</div><div class="v">{nice(stp.iloc[0]["item"])}</div>'
                          f'<div class="s">already in {stp.iloc[0]["base_rate"]:.0%} of baskets</div></div>', unsafe_allow_html=True)
        st.write("")
        shown = sa.dropna(subset=["confidence"])
        if len(shown):
            fig = go.Figure()
            for kind, colr in [("Natural", "#118AB2"), ("Campaign", "#EF476F"), ("Staple", "#9CA3AF")]:
                g = shown[shown["type"] == kind]
                if len(g):
                    fig.add_bar(name=kind, y=[nice(i) for i in g["item"]], x=g["confidence"] * 100, orientation="h", marker_color=colr,
                                text=[f"{v:.0%}" for v in g["confidence"]], textposition="outside", cliponaxis=False)
            fig.update_yaxes(autorange="reversed"); fig.update_xaxes(range=[0, 118])
            show(style(fig, f"Chance each item is added, given this basket ({seg2})", "Baskets like this one that add the item (%)",
                       "Item", 110 + 44 * len(shown)))
        table(sa.assign(Item=sa["item"].map(nice), Conf=sa["confidence"] * 100, Base=sa["base_rate"] * 100)[["Item", "type", "Conf", "Base", "lift", "baskets_used"]],
              column_config={"type": "Type", "Conf": st.column_config.NumberColumn("Added in similar baskets (%)", format="%.0f"),
                             "Base": st.column_config.NumberColumn("Added in any basket (%)", format="%.0f"),
                             "lift": st.column_config.NumberColumn("Lift", format="%.2f"),
                             "baskets_used": st.column_config.NumberColumn("Baskets compared", format="%d")})
        st.caption("Campaign items with no history in this segment show an empty chance: nobody has ordered them here yet.")
    insights([
        "<b>Offer the natural add-on first, then the campaign item:</b> the natural one has behaviour behind it; the campaign item builds exposure.",
        "<b>Skip staples:</b> a diner who adds cola 9 times in 10 needs no prompt, and a discount on it is a pure giveaway.",
        "<b>Baskets compared:</b> when fewer than 8 baskets match the full combination, the tool falls back to the strongest single item so the chance is never based on a handful of orders.",
    ])

# =============================================================================================
with tab3:
    section("If you can discount only one segment by 20%, which one?", "Money you keep from would-be churners minus the discount given to people who would have ordered anyway")
    d1, d2, d3, d4 = st.columns(4)
    disc = d1.slider("Discount", 0.05, 0.40, 0.20, 0.05, format="%.0f%%" if False else "%.2f", key="dc_disc")
    margin = d2.slider("Gross margin (assumption)", 0.20, 0.70, 0.35, 0.05, key="dc_margin", help="Not in the data. Set your real food margin.")
    win = d3.slider("Share of would-be churners the offer keeps", 0.05, 0.60, 0.25, 0.05, key="dc_win", help="Assumption. Validate with a pilot.")
    targeted = d4.toggle("Only offer to flagged at-risk diners", value=False, key="dc_target", help="Offer only to diners the churn model scores below 50% reorder.")
    sc = discount_scenario(A, disc, margin, win, targeted)
    best = sc["net"].idxmax()
    kpi_row([(s, f"{sc.loc[s, 'net']:+,.0f} AED", f"per month · {sc.loc[s, 'offered']:.0f} diners offered", SEG_COLORS[s]) for s in SEGMENTS])
    st.write("")
    if sc.loc[best, "net"] > 0:
        st.success(f"**Give it to {best}.** Estimated net {sc.loc[best, 'net']:+,.0f} AED a month at a {disc:.0%} discount, "
                   f"{margin:.0%} margin and {win:.0%} win-back. It breaks even if the offer keeps just {sc.loc[best, 'breakeven_win_rate']:.0%} of would-be churners.")
    else:
        st.error("**No segment pays back a blanket discount under these assumptions.** Switch on 'Only offer to flagged at-risk diners' or lower the discount.")
    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure()
        fig.add_bar(name="Revenue kept from would-be churners", x=SEGMENTS, y=sc["keep_gain"], marker_color="#06D6A0")
        fig.add_bar(name="Discount given to diners who stay anyway", x=SEGMENTS, y=-sc["subsidy"], marker_color="#EF476F")
        fig.add_scatter(name="Net", x=SEGMENTS, y=sc["net"], mode="markers+text", marker=dict(size=14, color="#1F2937"),
                        text=[f"{v:+,.0f}" for v in sc["net"]], textposition="top center")
        fig.update_layout(barmode="relative")
        show(style(fig, f"Monthly profit impact of a {disc:.0%} discount, by segment", "Segment", "AED per month", 400))
    with c2:
        fig = go.Figure()
        fig.add_bar(name="Would reorder anyway", x=SEGMENTS, y=sc["revenue_staying"] / 1000, marker_color="#C7D2FE")
        fig.add_bar(name="At risk of churning", x=SEGMENTS, y=sc["revenue_at_risk"] / 1000, marker_color="#EF476F")
        fig.update_layout(barmode="stack")
        show(style(fig, "Monthly revenue split: staying vs at-risk (model-estimated)", "Segment", "AED thousands per month", 400))
    sc2 = sc.reset_index()
    table(sc2[["segment", "diners", "offered", "reorder_rate", "already_discounted", "revenue_at_risk", "subsidy", "keep_gain", "net", "breakeven_win_rate"]],
          column_config={"segment": "Segment", "diners": "Diners", "offered": "Offered",
                         "reorder_rate": st.column_config.NumberColumn("Reorder rate", format="percent"),
                         "already_discounted": st.column_config.NumberColumn("Orders already discounted", format="percent"),
                         "revenue_at_risk": st.column_config.NumberColumn("At-risk revenue / mo", format="%.0f"),
                         "subsidy": st.column_config.NumberColumn("Discount cost / mo", format="%.0f"),
                         "keep_gain": st.column_config.NumberColumn("Revenue kept / mo", format="%.0f"),
                         "net": st.column_config.NumberColumn("Net / mo (AED)", format="%.0f"),
                         "breakeven_win_rate": st.column_config.NumberColumn("Break-even win-back", format="percent")})
    st.caption("Revenue = orders per month × average order value. At-risk share = 1 − out-of-fold reorder probability from the churn model. "
               "Margin, win-back rate and the idea that a discount changes behaviour are assumptions, not facts in the data.")
    stu, fam, pre = sc.loc["Budget students"], sc.loc["At-risk families"], sc.loc["Premium foodies"]
    insights([
        f"<b>Families are the only segment where a discount can pay:</b> {fam['revenue_at_risk'] / fam['monthly_revenue']:.0%} of their revenue is at risk, "
        f"so most of a discount reaches people who would otherwise leave.",
        f"<b>Students are the worst target:</b> {stu['reorder_rate']:.0%} already reorder and {stu['already_discounted']:.0%} of their orders are already discounted, "
        f"so a further 20% is almost all giveaway ({stu['subsidy']:,.0f} AED a month for {stu['keep_gain']:,.0f} kept).",
        f"<b>Premium foodies lose money on a blanket offer:</b> {pre['revenue_at_risk'] / pre['monthly_revenue']:.0%} of revenue is at risk, but they pay full price "
        f"and half of them would stay anyway. Use a non-price offer (a curated bundle) and give them a targeted offer only if flagged.",
        "<b>Target, don't blanket:</b> the same offer sent only to model-flagged diners costs far less and turns the families result clearly positive. Run it as a pilot with a control group.",
        "<b>The result depends on assumptions:</b> margin and win-back are not in the data. The break-even column shows how low the win-back can fall before the offer loses money.",
    ])

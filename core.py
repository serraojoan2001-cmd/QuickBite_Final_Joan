"""
core.py — QuickBite data, models and analytics.

Pure Python (no Streamlit import) so it can be tested or reused from a notebook.
`build_artifacts()` reproduces the whole case study from data/diners.csv and data/orders.csv:

    Task 1  K-Means segmentation          -> segment names, profiles, k selection table
    Task 2  Apriori basket analysis       -> rules overall and per segment
    Task 3  Random-forest reorder model   -> accuracy, confusion matrix, risk thresholds
    Bonus   Lifetime-spend regression     -> extension to the brief (not required by it)
    Task 4  Models for the live simulator -> scaler, kmeans, clf, reco (same keys as the brief)
"""
from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from sklearn.cluster import KMeans
from sklearn.ensemble import (GradientBoostingRegressor, RandomForestClassifier,
                              RandomForestRegressor)
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                             mean_absolute_error, r2_score, silhouette_score)
from sklearn.model_selection import (KFold, StratifiedKFold, cross_val_predict,
                                     cross_val_score, train_test_split)
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

# The five behaviour features used for clustering (order matters).
FEATURES = ["orders_per_month", "avg_order_value", "avg_items_per_order",
            "days_since_last_order", "discount_rate"]
CLF_FEATURES = FEATURES + ["age", "total_spend"]      # reorder classifier inputs
REG_FEATURES = FEATURES + ["age"]                     # spend regression inputs (no leakage of the target)

SEGMENTS = ["Budget students", "At-risk families", "Premium foodies"]
RADAR_LABELS = {      # short two-line labels so radar charts never clip at the edges
    "orders_per_month": "Orders<br>per month", "avg_order_value": "Avg order<br>value",
    "avg_items_per_order": "Items<br>per order", "days_since_last_order": "Days since<br>last order",
    "discount_rate": "Discount<br>rate"}
NICE = {
    "orders_per_month": "Orders per month",
    "avg_order_value": "Avg order value (AED)",
    "avg_items_per_order": "Items per order",
    "days_since_last_order": "Days since last order",
    "discount_rate": "Discount rate",
    "age": "Age",
    "total_spend": "Total spend (AED)",
}


# ----------------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------------
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    diners = pd.read_csv(DATA_DIR / "diners.csv").drop_duplicates()
    orders = pd.read_csv(DATA_DIR / "orders.csv")
    if set(diners["diner_id"]) != set(orders["diner_id"]):
        raise ValueError("diner_id values do not match between diners.csv and orders.csv")
    return diners, orders


# ----------------------------------------------------------------------------
# Association rules helpers
# ----------------------------------------------------------------------------
def mine_rules(basket_df: pd.DataFrame, min_support: float = 0.03, min_lift: float = 1.0) -> pd.DataFrame:
    freq = apriori(basket_df, min_support=min_support, use_colnames=True)
    try:
        rules = association_rules(freq, metric="lift", min_threshold=min_lift,
                                  num_itemsets=len(basket_df))
    except TypeError:                      # older mlxtend has no num_itemsets argument
        rules = association_rules(freq, metric="lift", min_threshold=min_lift)
    rules["antecedents"] = rules["antecedents"].apply(lambda s: ", ".join(sorted(s)))
    rules["consequents"] = rules["consequents"].apply(lambda s: ", ".join(sorted(s)))
    return rules.sort_values(["lift", "confidence"], ascending=False)


def top_pairs(rules: pd.DataFrame, n: int = 8) -> pd.DataFrame:
    """One-item -> one-item rules. A->B and B->A share the same lift, so keep the direction
    with the higher confidence (the more useful 'if they order A, they also order B')."""
    cols = ["rule", "antecedents", "consequents", "support", "confidence", "lift"]
    if rules.empty:
        return pd.DataFrame(columns=cols)
    r = rules[~rules["antecedents"].str.contains(",") & ~rules["consequents"].str.contains(",")].copy()
    r["pair"] = [tuple(sorted(p)) for p in zip(r["antecedents"], r["consequents"])]
    r["lift_r"] = r["lift"].round(6)
    r = r.sort_values(["lift_r", "confidence"], ascending=False).drop_duplicates("pair")
    r["rule"] = r["antecedents"] + " → " + r["consequents"]
    return r[cols].head(n).reset_index(drop=True)


# ----------------------------------------------------------------------------
# Build everything
# ----------------------------------------------------------------------------
def build_artifacts() -> dict:
    diners, orders = load_data()
    A: dict = {"features": FEATURES, "clf_features": CLF_FEATURES, "reg_features": REG_FEATURES}

    # ---- Task 1: segmentation ------------------------------------------------
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(diners[FEATURES])

    rows = []
    for k in range(2, 11):
        km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X_scaled)
        rows.append({"k": k, "inertia": km.inertia_, "silhouette": silhouette_score(X_scaled, km.labels_)})
    k_table = pd.DataFrame(rows)

    k_final = 3
    kmeans = KMeans(n_clusters=k_final, n_init=10, random_state=42).fit(X_scaled)
    diners["cluster"] = kmeans.labels_

    prof = diners.groupby("cluster")[FEATURES].mean()
    budget_id = prof["orders_per_month"].idxmax()          # most frequent orderers
    family_id = prof["avg_items_per_order"].idxmax()       # biggest baskets
    premium_id = ({0, 1, 2} - {budget_id, family_id}).pop()
    segment_names = {int(budget_id): "Budget students",
                     int(family_id): "At-risk families",
                     int(premium_id): "Premium foodies"}
    diners["segment"] = diners["cluster"].map(segment_names)

    summary = diners.groupby("segment").agg(
        diners=("diner_id", "count"),
        reorder_rate=("reordered", "mean"),
        orders_per_month=("orders_per_month", "mean"),
        avg_order_value=("avg_order_value", "mean"),
        avg_items_per_order=("avg_items_per_order", "mean"),
        days_since_last_order=("days_since_last_order", "mean"),
        discount_rate=("discount_rate", "mean"),
        age=("age", "mean"),
        total_spend_mean=("total_spend", "mean"),
        total_spend_sum=("total_spend", "sum"),
    ).reindex(SEGMENTS)
    spend_by_outcome = (diners.assign(outcome=np.where(diners["reordered"] == 1, "Reordered", "Churned"))
                        .groupby(["segment", "outcome"])["total_spend"].sum().unstack(fill_value=0)
                        .reindex(SEGMENTS))
    ranges = diners[FEATURES].agg(["min", "max"])
    A.update(diners=diners, orders=orders, scaler=scaler, kmeans=kmeans, segment_names=segment_names,
             k_table=k_table, k_final=k_final, segment_summary=summary,
             spend_by_outcome=spend_by_outcome, feature_ranges=ranges)

    # ---- Task 2: market-basket analysis --------------------------------------
    orders_seg = orders.merge(diners[["diner_id", "segment"]], on="diner_id")
    baskets = pd.crosstab(orders["order_id"], orders["item"]).gt(0)
    rules_all = mine_rules(baskets, 0.03)
    pairs = {"All diners": top_pairs(rules_all, 8)}
    for seg, grp in orders_seg.groupby("segment"):
        seg_baskets = pd.crosstab(grp["order_id"], grp["item"]).gt(0)
        try:
            pairs[seg] = top_pairs(mine_rules(seg_baskets, 0.03), 6)
        except Exception:                                   # no frequent itemsets
            pairs[seg] = top_pairs(pd.DataFrame(), 6)
    item_share = pd.crosstab(orders_seg["item"], orders_seg["segment"], normalize="columns")[SEGMENTS]
    basket_size = orders_seg.groupby(["segment", "order_id"]).size().groupby("segment").mean().reindex(SEGMENTS)
    reco = {seg: grp["item"].value_counts().head(5).index.tolist() for seg, grp in orders_seg.groupby("segment")}
    A.update(orders_seg=orders_seg, n_baskets=len(baskets), pairs=pairs, item_share=item_share,
             basket_size=basket_size, reco=reco)

    # ---- Task 3: reorder classifier ------------------------------------------
    X, y = diners[CLF_FEATURES], diners["reordered"]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    baseline = float(y_te.value_counts(normalize=True).max())
    clf = RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=42).fit(X_tr, y_tr)
    y_pred = clf.predict(X_te)
    cm = confusion_matrix(y_te, y_pred)                    # rows actual [churned, reordered]
    report = classification_report(y_te, y_pred, target_names=["churned", "reordered"], output_dict=True)
    cv = cross_val_score(RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=42),
                         X, y, cv=5)
    oof = cross_val_predict(RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=42),
                            X, y, cv=StratifiedKFold(5, shuffle=True, random_state=42), method="predict_proba")[:, 1]
    churned = (y == 0).to_numpy()
    thr_rows = []
    for t in np.arange(0.10, 0.91, 0.05):
        flagged = (1 - oof) >= t                           # flag as churn risk
        thr_rows.append({"threshold": round(float(t), 2),
                         "churners_caught": flagged[churned].mean(),
                         "loyal_flagged": flagged[~churned].mean(),
                         "precision": flagged[churned].sum() / max(flagged.sum(), 1)})
    A.update(clf=clf, clf_metrics={
        "accuracy": float(accuracy_score(y_te, y_pred)), "baseline": baseline, "cm": cm,
        "n_test": int(len(y_te)), "churn_caught": int(cm[0, 0]), "churn_missed": int(cm[0, 1]),
        "false_alarms": int(cm[1, 0]), "loyal_ok": int(cm[1, 1]), "churn_recall": float(report["churned"]["recall"]),
        "churn_precision": float(report["churned"]["precision"]), "cv_mean": float(cv.mean()),
        "cv_folds": cv.round(3).tolist()},
        clf_importance=pd.Series(clf.feature_importances_, index=CLF_FEATURES).sort_values(ascending=False),
        threshold_table=pd.DataFrame(thr_rows),
        oof_reorder=pd.Series(oof, index=diners.index, name="p_reorder"),
        reorder_corr=diners[CLF_FEATURES].corrwith(diners["reordered"]))

    # ---- Bonus: lifetime-spend regression ------------------------------------
    Xr, yr = diners[REG_FEATURES], diners["total_spend"]
    kf = KFold(5, shuffle=True, random_state=42)
    candidates = {"Linear regression": LinearRegression(),
                  "Random forest": RandomForestRegressor(n_estimators=300, random_state=42),
                  "Gradient boosting": GradientBoostingRegressor(random_state=42)}
    cv_r2 = {n: float(cross_val_score(m, Xr, yr, cv=kf, scoring="r2").mean()) for n, m in candidates.items()}
    best = max(cv_r2, key=cv_r2.get)
    oof_spend = cross_val_predict(candidates[best], Xr, yr, cv=kf)
    final = candidates[best].fit(Xr, yr)
    imp = getattr(final, "feature_importances_", None)
    if imp is None:
        imp = np.abs(final.coef_) / np.abs(final.coef_).sum()
    A.update(reg={
        "cv_r2": cv_r2, "best": best, "r2": float(r2_score(yr, oof_spend)),
        "mae": float(mean_absolute_error(yr, oof_spend)), "oof_pred": pd.Series(oof_spend, index=diners.index),
        "importance": pd.Series(imp, index=REG_FEATURES).sort_values(ascending=False),
        "corr": diners[REG_FEATURES].corrwith(diners["total_spend"])})
    return _extend(A)


# ----------------------------------------------------------------------------
# Live simulator + assignment export
# ----------------------------------------------------------------------------
def analyse_diner(A: dict, profile: dict) -> dict:
    """Segment, reorder probability and recommendations for one diner profile."""
    row = pd.DataFrame([profile])
    cluster = int(A["kmeans"].predict(A["scaler"].transform(row[FEATURES]))[0])
    seg = A["segment_names"][cluster]
    p_reorder = float(A["clf"].predict_proba(row[CLF_FEATURES])[0][1])
    pairs = A["pairs"].get(seg, pd.DataFrame())
    strong = pairs[pairs["lift"] >= 1.5].head(2) if len(pairs) else pairs
    return {"segment": seg, "p_reorder": p_reorder, "items": A["reco_ex"].get(seg, A["reco"].get(seg, [])),
            "staples": A["staples"].get(seg, []), "bundles": strong.to_dict("records")}


def export_models(A: dict, path: Path | str = ROOT / "food_models.joblib") -> Path:
    """Save the models in the exact dictionary format the original case-study app.py expects."""
    joblib.dump({"scaler": A["scaler"], "kmeans": A["kmeans"], "segment_names": A["segment_names"],
                 "clf": A["clf"], "features": FEATURES, "reco": A["reco"]}, path)
    return Path(path)


# ----------------------------------------------------------------------------
# What-if tools for the simulator
# ----------------------------------------------------------------------------
def segment_distances(A: dict, profile: dict) -> pd.Series:
    """Distance (in scaled units) from a diner to each segment's centre. Lower = closer = better fit."""
    row = pd.DataFrame([profile])
    z = A["scaler"].transform(row[FEATURES])[0]
    centres = A["kmeans"].cluster_centers_
    dist = np.sqrt(((centres - z) ** 2).sum(axis=1))
    return pd.Series({A["segment_names"][i]: float(dist[i]) for i in range(len(dist))}).reindex(SEGMENTS)


def sweep_feature(A: dict, profile: dict, feature: str, n: int = 41) -> pd.DataFrame:
    """Vary one feature across its observed range, keep the rest fixed; return segment and reorder probability."""
    lo, hi = float(A["diners"][feature].min()), float(A["diners"][feature].max())
    values = np.linspace(lo, hi, n)
    rows = pd.DataFrame([{**profile, feature: v} for v in values])
    clusters = A["kmeans"].predict(A["scaler"].transform(rows[FEATURES]))
    return pd.DataFrame({"value": values,
                         "segment": [A["segment_names"][int(c)] for c in clusters],
                         "p_reorder": A["clf"].predict_proba(rows[CLF_FEATURES])[:, 1]})


# ----------------------------------------------------------------------------
# Baskets, staples and menu exposure
# ----------------------------------------------------------------------------
KNOWN_COLUMNS = ["diner_id", "age", "orders_per_month", "avg_order_value", "avg_items_per_order",
                 "days_since_last_order", "discount_rate", "total_spend", "reordered"]


def _extend(A: dict) -> dict:
    """Second pass: basket matrix, staples, exposure, search directory (everything the extra pages need)."""
    o = A["orders_seg"]
    A["bk"] = pd.crosstab(o["order_id"], o["item"]).gt(0)
    A["bk_seg"] = o.drop_duplicates("order_id").set_index("order_id")["segment"].reindex(A["bk"].index)
    A["staples"] = detect_staples(A)
    A["reco_ex"] = {seg: [i for i in items if i not in A["staples"].get(seg, [])]
                    for seg, items in A["reco"].items()}
    A["exposure"] = item_exposure(A)
    A["extra_cols"] = [c for c in A["diners"].columns
                       if c not in KNOWN_COLUMNS + ["cluster", "segment"]]
    items = A["orders"].groupby("diner_id")["item"].agg(lambda x: sorted(set(x)))
    d = A["diners"].copy()
    d["items_ordered"] = d["diner_id"].map(items).apply(lambda v: v if isinstance(v, list) else [])
    d["status"] = np.where(d["reordered"] == 1, "Reordered", "Churned")
    A["directory"] = d
    return A


def basket_matrix(A: dict, segment: str = "All diners", exclude=()) -> pd.DataFrame:
    """True/False basket matrix. Excluded items are dropped as columns only, never as baskets, so every
    support figure keeps the same denominator (dropping small baskets would inflate the numbers)."""
    bk = A["bk"]
    if segment != "All diners":
        bk = bk.loc[(A["bk_seg"] == segment).to_numpy()]
    drop = [c for c in exclude if c in bk.columns]
    bk = bk.drop(columns=drop)
    return bk.loc[:, bk.any()]


def detect_staples(A: dict, min_share: float = 0.6, tol: float = 0.10) -> dict:
    """A staple is in most of a segment's baskets AND is independent of everything else (lift within
    +/- tol of 1 with every other item): it is a habit add-on, not a pairing."""
    out = {}
    for seg in SEGMENTS:
        bk = basket_matrix(A, seg)
        share = bk.mean()
        found = []
        for item in share.index[share >= min_share]:
            lifts = [(bk[item] & bk[c]).mean() / (share[item] * share[c]) for c in bk.columns if c != item]
            if lifts and max(abs(l - 1) for l in lifts) <= tol:
                found.append(item)
        out[seg] = found
    return out


def item_exposure(A: dict) -> pd.DataFrame:
    """Per item: baskets, share of all baskets, share within each segment, exposure class."""
    bk = A["bk"]
    df = pd.DataFrame({"baskets": bk.sum()})
    df["share_all"] = df["baskets"] / len(bk)
    for seg in SEGMENTS:
        df[seg] = basket_matrix(A, seg).mean().reindex(df.index).fillna(0.0)
    df["sold_to"] = (df[SEGMENTS] > 0).sum(axis=1)
    lo, hi = df["baskets"].quantile(1 / 3), df["baskets"].quantile(2 / 3)
    df["exposure"] = np.where(df["baskets"] <= lo, "Under-exposed", np.where(df["baskets"] >= hi, "Best-seller", "Mid"))
    return df.sort_values("baskets")


def pairs_excluding(A: dict, segment: str = "All diners", exclude=(), n: int = 8, min_support: float = 0.03) -> pd.DataFrame:
    bk = basket_matrix(A, segment, exclude)
    try:
        return top_pairs(mine_rules(bk, min_support), n)
    except Exception:
        return top_pairs(pd.DataFrame(), n)


def staple_evidence(A: dict, item: str = "cola") -> dict:
    """Everything needed to judge whether `item` is a habit add-on that distorts the picture."""
    bk, seg_bk = A["bk"], {s: basket_matrix(A, s) for s in SEGMENTS}
    share_seg = {s: float(b[item].mean()) if item in b else 0.0 for s, b in seg_bk.items()}
    home = max(share_seg, key=share_seg.get)                       # segment where the item lives
    hb = seg_bk[home]
    mains = [c for c in hb.columns if c != item and hb[c].mean() >= 0.15]
    attach = {m: float(hb.loc[hb[m], item].mean()) for m in mains}
    attach["Any other item"] = float(hb[item].mean())
    lifts = {c: float((hb[item] & hb[c]).mean() / (hb[item].mean() * hb[c].mean())) for c in mains}
    size_with = {s: float(b.sum(axis=1).mean()) for s, b in seg_bk.items()}
    size_without = {s: float(b.drop(columns=[item], errors="ignore").sum(axis=1).mean()) for s, b in seg_bk.items()}
    empty = int((hb.sum(axis=1).eq(1) & hb[item]).sum())
    return {"item": item, "home": home, "share_all": float(bk[item].mean()), "share_seg": share_seg,
            "attach": attach, "attach_base": float(hb[item].mean()), "lifts": lifts,
            "size_with": size_with, "size_without": size_without, "empty_home": empty, "n_home": len(hb)}


# ----------------------------------------------------------------------------
# Promo bundles + live basket upsell
# ----------------------------------------------------------------------------
TIER_ORDER = ["Strong pull", "Some pull", "No pull", "No history"]


def bundle_candidates(A: dict, segment: str, promo: str, proxy: str | None = None,
                      take_rate: float = 0.10, min_anchor_share: float = 0.10) -> pd.DataFrame:
    """Rank the frequently-ordered items ('anchors') a promoted item could be attached to.

    - promo already on the menu: history comes from its own orders in this segment.
    - promo is a NEW item (not in the data): pass `proxy`, an existing item it is expected to behave like;
      nobody has it yet, so every basket holding the anchor is an opportunity.
    """
    bk = basket_matrix(A, segment)
    n = len(bk)
    is_new = promo not in A["bk"].columns
    ref = proxy if is_new else promo
    ref_share = float(bk[ref].mean()) if ref in bk.columns else 0.0
    rows = []
    for x in bk.columns:
        if x in (promo, ref):
            continue
        share_x = float(bk[x].mean())
        if share_x < min_anchor_share:
            continue
        n_x = int(bk[x].sum())
        together = int((bk[x] & bk[ref]).sum()) if ref in bk.columns else 0
        lift = (together / n) / (share_x * ref_share) if (ref_share > 0 and together > 0) else 0.0
        if ref_share == 0 or together == 0:
            tier = "No history"
        elif lift >= 1.5:
            tier = "Strong pull"
        elif lift >= 1.2:
            tier = "Some pull"
        else:
            tier = "No pull"
        gap = n_x if is_new else n_x - together
        rows.append({"anchor": x, "anchor_share": share_x, "anchor_baskets": n_x, "together": together,
                     "confidence": together / n_x, "lift": lift, "evidence": tier, "gap": gap,
                     "est_new": gap * take_rate, "projected": is_new})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["tier_rank"] = df["evidence"].map({t: i for i, t in enumerate(TIER_ORDER)})
    return df.sort_values(["tier_rank", "est_new"], ascending=[True, False]).drop(columns="tier_rank").reset_index(drop=True)


def campaign_shortlist(A: dict, take_rate: float = 0.10) -> pd.DataFrame:
    """Best PROVEN bundle (strong or some pull) per segment, attaching under-exposed items to best-sellers."""
    exp = A["exposure"]
    under = exp.index[exp["exposure"] == "Under-exposed"]
    rows = []
    for seg in SEGMENTS:
        best = None
        for promo in under:
            if exp.loc[promo, seg] == 0:
                continue
            c = bundle_candidates(A, seg, promo, take_rate=take_rate)
            c = c[c["evidence"].isin(["Strong pull", "Some pull"]) & (c["gap"] > 0)]
            if len(c):
                top = c.sort_values("est_new", ascending=False).iloc[0]
                if best is None or top["est_new"] > best["est_new"]:
                    best = {"segment": seg, "promo": promo, **top.to_dict()}
        rows.append(best or {"segment": seg, "promo": None})
    return pd.DataFrame(rows)


def suggest_addons(A: dict, segment: str, basket: list, promo: list | tuple = (), min_n: int = 8) -> pd.DataFrame:
    """What to offer next, given the items already in a customer's basket."""
    bk = basket_matrix(A, segment)
    basket = [b for b in basket if b in bk.columns]
    staples = A["staples"].get(segment, [])
    base = bk.mean()
    sub = bk[bk[basket].all(axis=1)] if basket else bk
    rows = []
    for c in bk.columns:
        if c in basket:
            continue
        conf, used = np.nan, 0
        if len(sub) >= min_n:
            conf, used = float(sub[c].mean()), len(sub)
        else:                                         # too few baskets hold the whole combination: best single item
            for b in basket:
                nb = int(bk[b].sum())
                if nb >= min_n:
                    cb = float(bk.loc[bk[b], c].mean())
                    if np.isnan(conf) or cb > conf:
                        conf, used = cb, nb
        kind = "Campaign" if c in promo else ("Staple" if c in staples else "Natural")
        rows.append({"item": c, "confidence": conf, "base_rate": float(base[c]),
                     "lift": conf / base[c] if base[c] > 0 and not np.isnan(conf) else np.nan,
                     "baskets_used": used, "type": kind})
    for c in promo:                                    # promoted items the segment has never ordered
        if c not in bk.columns and c not in basket:
            rows.append({"item": c, "confidence": np.nan, "base_rate": 0.0, "lift": np.nan,
                         "baskets_used": 0, "type": "Campaign"})
    df = pd.DataFrame(rows)
    return df.sort_values(["confidence"], ascending=False, na_position="last").reset_index(drop=True) if len(df) else df


# ----------------------------------------------------------------------------
# 20% discount scenario
# ----------------------------------------------------------------------------
def discount_scenario(A: dict, discount: float = 0.20, margin: float = 0.35, win_rate: float = 0.25,
                      targeted: bool = False, threshold: float = 0.5) -> pd.DataFrame:
    """Monthly profit impact (AED) of giving `discount` to ONE segment, for each segment.

    For every diner i (revenue_i = orders per month x average order value, p_i = cross-validated reorder probability):
      keep gain  = win_rate x (1 - p_i) x revenue_i x (margin - discount)   # would-be churners the offer keeps
      subsidy    = discount x p_i x revenue_i                                 # discount on orders that happen anyway
      net        = keep gain - subsidy
    `margin` and `win_rate` are assumptions (not in the data); p_i comes from the churn model.
    With targeted=True only diners the model flags as at-risk (p_i < threshold) receive the offer.
    """
    d = A["diners"].assign(p=A["oof_reorder"], rev=lambda x: x["orders_per_month"] * x["avg_order_value"])
    rows = []
    for seg in SEGMENTS:
        g = d[d["segment"] == seg]
        grp = g[g["p"] < threshold] if targeted else g
        stay, risk = float((grp["p"] * grp["rev"]).sum()), float(((1 - grp["p"]) * grp["rev"]).sum())
        cost = discount * stay
        gain = win_rate * risk * (margin - discount)
        be = cost / (risk * (margin - discount)) if (margin > discount and risk > 0) else np.nan
        rows.append({"segment": seg, "diners": len(g), "offered": len(grp), "monthly_revenue": float(g["rev"].sum()),
                     "revenue_at_risk": float(((1 - g["p"]) * g["rev"]).sum()), "revenue_staying": float((g["p"] * g["rev"]).sum()),
                     "offer_at_risk": risk, "offer_staying": stay, "subsidy": cost, "keep_gain": gain, "net": gain - cost,
                     "breakeven_win_rate": be, "already_discounted": float(g["discount_rate"].mean()),
                     "reorder_rate": float(g["reordered"].mean())})
    return pd.DataFrame(rows).set_index("segment").reindex(SEGMENTS)


# ----------------------------------------------------------------------------
# Diner search (ID, segment, status, items, plus any extra text columns such as name / email)
# ----------------------------------------------------------------------------
def search_fields(A: dict) -> list[str]:
    return ["diner ID", "segment", "reorder status", "items ordered"] + list(A["extra_cols"])


def search_diners(A: dict, query: str = "", segments=(), status: str = "Any", age=None, days=None,
                  opm=None, items=()) -> pd.DataFrame:
    d = A["directory"]
    text_cols = ["diner_id", "segment", "status"] + list(A["extra_cols"])
    blob = d[text_cols].astype(str).agg(" ".join, axis=1).str.lower()
    blob = blob + " " + d["items_ordered"].apply(lambda l: " ".join(l) + " " + " ".join(i.replace("_", " ") for i in l))
    mask = pd.Series(True, index=d.index)
    for tok in query.lower().split():
        mask &= blob.str.contains(tok, regex=False)
    if segments:
        mask &= d["segment"].isin(segments)
    if status != "Any":
        mask &= d["status"] == status
    if age:
        mask &= d["age"].between(*age)
    if days:
        mask &= d["days_since_last_order"].between(*days)
    if opm:
        mask &= d["orders_per_month"].between(*opm)
    if items:
        mask &= d["items_ordered"].apply(lambda l: any(i in l for i in items))
    return d[mask].sort_values("diner_id")

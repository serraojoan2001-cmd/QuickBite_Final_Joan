# 🍔 QuickBite — Diner Intelligence Dashboard

Interactive Streamlit dashboard built from the QuickBite "Know Your Diners" case study:
segments, basket combos, churn prediction, a spend forecast and a live diner simulator.

## Pages

| Page (sidebar label) | Role | File |
|---|---|---|
| 📊 Business Snapshot | Executive summary — every answer at a glance, plus the **Customer Fact Sheet** (what to remember about each segment and the early-warning signals) | `views/snapshot.py` |
| 👥 Diner Segments | Clustering (K-Means, k chosen by elbow + silhouette) | `views/segments.py` |
| 🛒 Basket Combos | Association rules (Apriori) — overall and per segment | `views/combos.py` |
| 🎯 Churn Radar | Classification — who will reorder? | `views/churn.py` |
| 💰 Spend Forecast | Regression — predicts total spend (bonus, not in the original brief) | `views/spend.py` |
| 🔮 Diner Simulator | **Live demo** — type a diner, get segment, reorder likelihood, recommended items | `views/simulator.py` |

Every page ends with a **Key insights** box. All numbers in it are computed from the data, not typed in.

## Files

| File | What it is |
|---|---|
| `app.py` | Entry point: page setup, sidebar navigation, trains/caches models once |
| `core.py` | Data loading + all analytics and models (no Streamlit code) |
| `ui.py` | Colours, CSS, KPI cards, chart styling, insight box |
| `views/` | One file per dashboard page (see table above) |
| `data/diners.csv`, `data/orders.csv` | The case-study data |
| `requirements.txt` | Python packages Streamlit Cloud installs |
| `.streamlit/config.toml` | Colour theme |
| `train_models.py` | Optional: re-creates `food_models.joblib` for the original case-study `app.py` |
| `food_models.joblib` | Optional: models in the format the original case-study dashboard expects |
| `.gitignore` | Keeps cache files out of GitHub |

The dashboard does **not** read `food_models.joblib`. It trains the same models at start-up
(about 15 seconds, then cached; `random_state = 42`), so a scikit-learn version mismatch can never break a deployment.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy: GitHub → Streamlit Community Cloud

1. Create an empty repository on GitHub (for example `quickbite-dashboard`).
2. In this folder run:
   ```bash
   git init
   git add .
   git commit -m "QuickBite dashboard"
   git branch -M main
   git remote add origin https://github.com/<your-username>/quickbite-dashboard.git
   git push -u origin main
   ```
3. Go to https://share.streamlit.io and sign in with GitHub.
4. Click **Create app** → choose the repository, branch `main`, main file path `app.py`.
5. Under **Advanced settings** pick Python 3.11 or 3.12, then click **Deploy**.

The first load takes about a minute while packages install and models train.


## Added: Campaign Planner, multi-field diner search, cola staple check
- **📣 Campaign Planner** (Action group): promo bundles for under-exposed or brand-new items (stand-in item for items with no history), live basket upsell, and the 20% discount decision (editable margin / win-back assumptions).
- **Diner Simulator** search now matches every word across diner ID, segment, outcome, items ordered and any extra text column (name, email...) if you add one to `data/diners.csv`. Filters: segment, outcome, age, recency, items. **Real names/emails are personal data: do not commit them to a public GitHub repo.**
- **Basket Combos**: "Hide items" control and a cola staple check.

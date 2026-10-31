"""
app.py — QuickBite Diner Intelligence (entry point).

Run locally:   streamlit run app.py
Deploy:        push this folder to GitHub, then create the app on https://share.streamlit.io
               (main file path: app.py)
"""
import streamlit as st

from ui import get_artifacts, inject_css

st.set_page_config(page_title="QuickBite Diner Intelligence", page_icon="🍔", layout="wide")
inject_css()

pages = {
    "Overview": [
        st.Page("views/snapshot.py", title="Business Snapshot", icon="📊", default=True),
    ],
    "Analysis": [
        st.Page("views/segments.py", title="Diner Segments", icon="👥"),
        st.Page("views/combos.py", title="Basket Combos", icon="🛒"),
        st.Page("views/churn.py", title="Churn Radar", icon="🎯"),
        st.Page("views/spend.py", title="Spend Forecast", icon="💰"),
    ],
    "Action": [
        st.Page("views/campaign.py", title="Campaign Planner", icon="📣"),
    ],
    "Live demo": [
        st.Page("views/simulator.py", title="Diner Simulator", icon="🔮"),
    ],
}

with st.sidebar:
    st.markdown('<div class="brand">🍔 QuickBite</div><div class="brand-s">Diner Intelligence Dashboard</div>',
                unsafe_allow_html=True)

get_artifacts()          # train once and cache; later pages open instantly
st.navigation(pages).run()

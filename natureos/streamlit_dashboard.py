"""Simple Streamlit dashboard displaying MAS board metrics."""

import streamlit as st

st.set_page_config(page_title="MAS Board Metrics", layout="wide")

st.title("Mycosoft MAS Metrics Dashboard")

placeholder = st.empty()

with placeholder.container():
    st.metric("Active Agents", 0)
    st.metric("Pending Tasks", 0)
    st.metric("System Health", "Unknown")

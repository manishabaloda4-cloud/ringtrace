"""
RingTrace — Streamlit UI

Run with: streamlit run ui/app.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
from agents.detection import run_all_detections, get_account_context
from agents.explainer import explain_findings, explain_account

st.set_page_config(page_title="RingTrace — UPI Fraud Ring Detector", page_icon="🕸️", layout="wide")

st.title("🕸️ RingTrace")
st.caption("Graph-based UPI fraud ring detection — finds *rings*, not just flagged transactions")

with st.sidebar:
    st.header("⚙️ Settings")
    language = st.radio("Explanation language", ["English", "Hindi"], horizontal=True)
    st.markdown("---")
    st.markdown(
        "**How it works:** transactions are modeled as a graph. RingTrace runs "
        "3 real fraud-detection patterns via Cypher graph queries, then an LLM "
        "agent explains the findings in plain language."
    )
    st.markdown("---")
    st.caption("⚠️ Demo dataset is synthetically generated with planted fraud "
               "patterns for demonstration. Architecture is built to run against "
               "real transaction feeds in production.")

tab1, tab2 = st.tabs(["🔍 Full Network Scan", "🔎 Look Up an Account"])

with tab1:
    st.subheader("Run detection across the full transaction graph")
    if st.button("Run RingTrace Scan", type="primary"):
        with st.spinner("Running graph detection (cycles, fan-out, shared-device)..."):
            findings = run_all_detections()

        col1, col2, col3 = st.columns(3)
        col1.metric("Cyclic rings found", len(findings["cycles"]))
        col2.metric("Fan-out clusters found", len(findings["fanout"]))
        col3.metric("Shared-device clusters found", len(findings["shared_device"]))

        st.markdown("### 🧠 Analyst Explanation")
        with st.spinner("Generating explanation..."):
            explanation = explain_findings(findings, language=language.lower())
        st.info(explanation)

        st.markdown("### 🕸️ Flagged Network Graph")
        nodes = {}
        edges = []

        for ring in findings["cycles"]:
            ids = ring["ring"]
            for aid in ids:
                nodes[aid] = Node(id=aid, label=aid, color="#E63946", size=22)
            for i in range(len(ids) - 1):
                edges.append(Edge(source=ids[i], target=ids[i + 1], color="#E63946"))

        for fo in findings["fanout"]:
            src = fo["source"]
            nodes[src] = Node(id=src, label=src, color="#F4A261", size=26)
            for tgt in fo["targets"]:
                nodes[tgt] = Node(id=tgt, label=tgt, color="#F4A261", size=16)
                edges.append(Edge(source=src, target=tgt, color="#F4A261"))

        for cluster in findings["shared_device"]:
            accs = cluster["linked_accounts"]
            for aid in accs:
                nodes[aid] = Node(id=aid, label=aid, color="#8E44AD", size=20)
            for i in range(len(accs) - 1):
                edges.append(Edge(source=accs[i], target=accs[i + 1], color="#8E44AD"))

        if nodes:
            config = Config(width=1100, height=500, directed=True, physics=True,
                             hierarchical=False)
            agraph(nodes=list(nodes.values()), edges=edges, config=config)
        else:
            st.warning("No suspicious patterns found in current dataset.")

with tab2:
    st.subheader("Look up a specific account")
    account_id = st.text_input("Account ID", placeholder="e.g. ACC0121")
    if st.button("Investigate Account"):
        if not account_id:
            st.warning("Enter an account ID first.")
        else:
            with st.spinner("Fetching account context..."):
                context = get_account_context(account_id)
            if not context:
                st.error(f"Account {account_id} not found.")
            else:
                st.json(context)
                with st.spinner("Generating explanation..."):
                    explanation = explain_account(account_id, context, language=language.lower())
                st.info(explanation)

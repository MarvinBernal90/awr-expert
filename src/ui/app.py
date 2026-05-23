"""
Streamlit Web Interface for AWR Expert.
Consumes the FastAPI backend to render an Executive Dashboard.
"""

import os
from typing import Any, Dict, List

import plotly.graph_objects as go
import requests
import streamlit as st

# API Server Configuration
API_URL = os.getenv("AWR_API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="AWR Expert", page_icon="🧠", layout="wide")
st.title("🧠 AWR Expert: Cognitive Dashboard")
st.markdown("Enterprise AI and Behavioral Analytics for Oracle Databases")


def render_behavioral_chart(
    m_name: str, display_name: str, m_data: Dict[str, Any], raw_series: List[Dict]
):
    """Generates an interactive Plotly chart for time-series evaluation."""
    # Extract and sort chronologically (assuming DuckDB returns newest at end)
    y_vals = [float(s.get(m_name, 0)) for s in raw_series]

    current_val = m_data.get("current", 0)
    p95 = m_data.get("p95", 0)
    status = m_data.get("status", "NORMAL")

    # Semantic colors for status indication
    marker_color = "#00CC96"  # Green (Normal)
    if "CRITICAL" in status:
        marker_color = "#EF553B"  # Red
    elif "WARNING" in status:
        marker_color = "#FFA15A"  # Orange

    fig = go.Figure()

    # 1. Historical line (Gray)
    fig.add_trace(
        go.Scatter(
            y=y_vals,
            mode="lines+markers",
            name="History",
            line=dict(color="rgba(150, 150, 150, 0.4)", width=2),
            marker=dict(size=6, color="rgba(150, 150, 150, 0.6)"),
        )
    )

    # 2. P95 Line (Dotted Blue)
    if p95 > 0:
        fig.add_hline(
            y=p95,
            line_dash="dot",
            line_color="#636EFA",
            annotation_text=f"P95: {p95}",
            annotation_position="top right",
        )

    # 3. Current Snapshot (Highlighted point)
    fig.add_trace(
        go.Scatter(
            x=[len(y_vals)],  # Place it at the end of the series
            y=[current_val],
            mode="markers+text",
            name="Current",
            text=[f"{current_val}"],
            textposition="top center",
            marker=dict(size=14, color=marker_color, symbol="diamond"),
        )
    )

    fig.update_layout(
        title=dict(text=f"{display_name} ({status})", font=dict(size=14)),
        margin=dict(l=20, r=20, t=40, b=20),
        showlegend=False,
        height=250,
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(200, 200, 200, 0.2)"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)


with st.sidebar:
    st.header("⚙️ AWR Ingestion")
    uploaded_file = st.file_uploader("Upload your AWR report (HTML)", type=["html"])

if uploaded_file:
    file_id = id(uploaded_file)
    if st.session_state.get("current_file_id") != file_id:
        st.session_state["current_file_id"] = file_id
        st.session_state.pop("analysis_data", None)

    run_analysis = st.sidebar.button("Run AI Analysis")
    if run_analysis:
        st.session_state.pop("analysis_data", None)

    if run_analysis or "analysis_data" in st.session_state:
        if "analysis_data" not in st.session_state:
            with st.spinner("Executing Cognitive Engine..."):
                files = {
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        "text/html",
                    )
                }
                try:
                    upload_res = requests.post(f"{API_URL}/upload", files=files)
                    upload_res.raise_for_status()
                    awr_hash = upload_res.json()["awr_hash"]

                    analysis_res = requests.get(f"{API_URL}/analyze/{awr_hash}")
                    analysis_res.raise_for_status()

                    st.session_state["analysis_data"] = {
                        "upload": upload_res.json(),
                        "analysis": analysis_res.json(),
                    }

                except Exception as e:
                    st.error(f"🚨 Integration Error: {str(e)}")
                    st.stop()

        # Data rendering
        data = st.session_state["analysis_data"]
        upload_data = data["upload"]
        analysis_data = data["analysis"]

        st.sidebar.success("✅ Context Loaded")
        st.sidebar.info(f"**DB:** {upload_data['db_name']}")

        # --- LEVEL 1: WORKLOAD PROFILE ---
        wl = analysis_data.get("workload_profile", {})
        st.header("🤖 Workload Profile")
        col_w1, col_w2, col_w3 = st.columns([1, 1, 2])
        col_w1.metric("Pattern", wl.get("workload_type", "UNKNOWN"))
        col_w2.metric("Confidence", f"{wl.get('confidence', 0)}%")
        col_w3.info(f"**Reasoning:** {wl.get('reason', '')}")
        st.markdown("---")

        # --- LEVEL 2: BEHAVIORAL ANALYSIS (PLOTLY) ---
        behav = analysis_data.get("behavioral_analysis", {})
        history_size = behav.get("history_size", 0)

        st.header(f"📈 Behavioral Analytics (Last {history_size} snapshots)")

        if history_size > 0:
            metrics_data = behav.get("metrics", {})
            raw_series = behav.get("raw_time_series", [])

            # 2x2 matrix layout for the charts
            m_mappings = [
                ("logical_reads_ps", "Logical Reads/s"),
                ("physical_reads_ps", "Physical Reads/s"),
                ("executes_ps", "Executes/s"),
                ("transactions_ps", "Transactions/s"),
            ]

            g_col1, g_col2 = st.columns(2)

            for idx, (m_key, display) in enumerate(m_mappings):
                target_col = g_col1 if idx % 2 == 0 else g_col2
                with target_col:
                    m_eval = metrics_data.get(m_key, {})
                    render_behavioral_chart(m_key, display, m_eval, raw_series)
        else:
            st.warning("Not enough historical data to compute baselines.")

        st.markdown("---")

        # --- LEVEL 3: STRUCTURED DIAGNOSTICS ---
        st.header("📊 Structured Diagnostics")
        diagnostics = analysis_data.get("diagnostics", [])

        if not diagnostics:
            st.success("No active bottlenecks detected.")
        else:
            for diag in diagnostics:
                color = "🔴" if diag["severity"] == "CRITICAL" else "🟡"
                header = f"{color} {diag['area']} - {diag['status']}"
                with st.expander(header, expanded=True):
                    st.write(f"**Impact:** {diag['impact']}")
                    st.write(f"**Recommendation:** {diag['recommendation']}")
                    st.markdown("**Evidence:**")
                    for f in diag["findings"]:
                        st.markdown(f"- {f['description']}")

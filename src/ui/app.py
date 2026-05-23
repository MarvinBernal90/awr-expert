"""
Streamlit Web Interface for AWR Expert.
Consumes the FastAPI backend to render an Executive Dashboard.
"""

import os

import requests
import streamlit as st

# API Server Configuration (Support for Docker/Cloud deployments)
API_URL = os.getenv("AWR_API_URL", "http://127.0.0.1:8000")

# Page Configuration
st.set_page_config(page_title="AWR Expert", page_icon="🧠", layout="wide")

st.title("🧠 AWR Expert: Executive Dashboard")
st.markdown("Heuristic Intelligence for Oracle Databases")

# Sidebar for file upload
with st.sidebar:
    st.header("⚙️ AWR Ingestion")
    uploaded_file = st.file_uploader("Upload your AWR report (HTML)", type=["html"])

if uploaded_file:
    # Detect if file content changed by tracking file ID
    file_id = id(uploaded_file)
    if st.session_state.get("current_file_id") != file_id:
        st.session_state["current_file_id"] = file_id
        st.session_state.pop("analysis_data", None)

    # Execution trigger
    run_analysis = st.sidebar.button("Run AI Analysis")

    # Clear cache if user explicitly requests re-analysis
    if run_analysis:
        st.session_state.pop("analysis_data", None)

    if run_analysis or "analysis_data" in st.session_state:
        # Only call the API if we don't have the data in cache
        if "analysis_data" not in st.session_state:
            with st.spinner("Analyzing report with heuristic engine..."):
                files = {
                    "file": (uploaded_file.name, uploaded_file.getvalue(), "text/html")
                }
                try:
                    # 1. Send the file to the FastAPI backend
                    upload_res = requests.post(
                        f"{API_URL}/upload", files=files, timeout=30
                    )
                    upload_res.raise_for_status()
                    upload_data = upload_res.json()
                    awr_hash = upload_data["awr_hash"]

                    # 2. Query diagnostics
                    analysis_res = requests.get(
                        f"{API_URL}/analyze/{awr_hash}", timeout=30
                    )
                    analysis_res.raise_for_status()
                    analysis_json = analysis_res.json()

                    # 3. Cache the results in Streamlit session state
                    st.session_state["analysis_data"] = {
                        "upload_data": upload_data,
                        "workload": analysis_json.get("workload_profile", {}),
                        "diagnostics": analysis_json.get("diagnostics", []),
                    }

                except requests.exceptions.Timeout:
                    st.error("🚨 Request timed out. The backend took too long.")
                    st.stop()
                except requests.exceptions.ConnectionError:
                    st.error(
                        "🚨 Connection error. Ensure your FastAPI "
                        "server is running on port 8000."
                    )
                    st.stop()
                except requests.exceptions.HTTPError as e:
                    try:
                        err_msg = e.response.json().get("detail", str(e))
                    except Exception:
                        err_msg = str(e)
                    st.error(f"🚨 API Error: {err_msg}")
                    st.stop()

        # Render data directly from the cache
        data = st.session_state["analysis_data"]
        upload_data = data["upload_data"]
        workload = data["workload"]
        diagnostics = data["diagnostics"]

        # Show basic info in the sidebar
        st.sidebar.success("✅ File successfully processed")
        st.sidebar.info(
            f"**DB:** {upload_data['db_name']}\n\n"
            f"**Elapsed Time:** {upload_data['elapsed_mins']} min"
        )

        # --- LEVEL 2: CONTEXT AWARENESS & BASELINES ---
        st.header("🤖 AI Context Awareness")
        if workload:
            wl_type = workload.get("workload_type", "UNKNOWN")
            wl_conf = workload.get("confidence", 0.0)
            wl_reason = workload.get("reason", "")

            wl_col1, wl_col2, wl_col3 = st.columns([1, 1, 2])
            with wl_col1:
                st.metric(label="Detected Profile", value=wl_type)
            with wl_col2:
                st.metric(label="AI Confidence", value=f"{wl_conf}%")
            with wl_col3:
                st.info(f"**Reasoning:** {wl_reason}")

            # SPRINT 12: DYNAMIC BASELINES VISUALIZATION
            baselines = workload.get("baselines", {})
            if baselines and baselines.get("history_size", 0) > 0:
                title = (
                    f"### 📈 Historical Baselines "
                    f"(Based on {baselines['history_size']} past reports)"
                )
                st.markdown(title)
                metrics_data = baselines.get("metrics", {})

                b_cols = st.columns(4)
                metric_mappings = [
                    ("logical_reads_ps", "Logical Reads /s"),
                    ("physical_reads_ps", "Physical Reads /s"),
                    ("executes_ps", "Executes /s"),
                    ("transactions_ps", "Transactions /s"),
                ]

                for i, (m_key, m_name) in enumerate(metric_mappings):
                    m_data = metrics_data.get(m_key, {})
                    if m_data:
                        current = m_data.get("current", 0)
                        pct = m_data.get("deviation_pct", 0)
                        status = m_data.get("status", "NORMAL")

                        # Formatting the delta visualization
                        delta_val = f"{pct}%" if pct <= 0 else f"+{pct}%"
                        if status == "HIGH":
                            delta_val += " ⬆️"
                        elif status == "LOW":
                            delta_val += " ⬇️"
                        else:
                            delta_val += " ➖"

                        with b_cols[i]:
                            st.metric(
                                label=m_name,
                                value=current,
                                delta=delta_val,
                                delta_color="off",
                            )
        else:
            st.warning("⚠️ Context engine skipped or unavailable.")

        st.markdown("---")

        # --- DIAGNOSTICS DASHBOARD ---
        st.header("📊 Overall Health Score")

        if not diagnostics:
            st.success(
                "✨ All good! No critical bottlenecks detected. "
                "The database is healthy."
            )
        else:
            for diag in diagnostics:
                severity = diag["severity"]
                if severity == "CRITICAL":
                    color = "🔴"
                    msg_type = st.error
                elif severity == "WARN":
                    color = "🟡"
                    msg_type = st.warning
                else:
                    color = "🟢"
                    msg_type = st.success

                with st.container():
                    st.subheader(f"{color} {diag['area']}")

                    col1, col2 = st.columns([1, 3])

                    with col1:
                        st.metric(label="Status", value=diag["status"])
                        st.metric(label="Impact", value=diag["impact"])

                    with col2:
                        msg_type(f"**Recommendation:** {diag['recommendation']}")

                        with st.expander(
                            "🔍 Skeptical DBA Mode (View Technical Evidence)"
                        ):
                            findings = diag["findings"]
                            if not findings:
                                st.write("No additional engine-level evidence.")
                            else:
                                for f in findings:
                                    icon = "🚩" if f["is_critical"] else "ℹ️"
                                    st.markdown(f"- {icon} {f['description']}")

                    st.markdown("---")

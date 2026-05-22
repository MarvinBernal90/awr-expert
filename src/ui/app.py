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
    # Detect if a new file was uploaded to clear previous cache
    if st.session_state.get("current_file") != uploaded_file.name:
        st.session_state["current_file"] = uploaded_file.name
        st.session_state.pop("analysis_data", None)

    # Execution trigger
    if st.sidebar.button("Run AI Analysis") or "analysis_data" in st.session_state:
        # Only call the API if we don't have the data in cache
        if "analysis_data" not in st.session_state:
            with st.spinner("Analyzing report with heuristic engine..."):
                files = {
                    "file": (uploaded_file.name, uploaded_file.getvalue(), "text/html")
                }
                try:
                    # 1. Send the file to the FastAPI backend (with explicit timeout)
                    upload_res = requests.post(
                        f"{API_URL}/upload", files=files, timeout=30
                    )
                    upload_res.raise_for_status()
                    upload_data = upload_res.json()
                    awr_hash = upload_data["awr_hash"]

                    # 2. Query diagnostics (with explicit timeout)
                    analysis_res = requests.get(
                        f"{API_URL}/analyze/{awr_hash}", timeout=30
                    )
                    analysis_res.raise_for_status()
                    diagnostics = analysis_res.json()["diagnostics"]

                    # 3. Cache the results in Streamlit session state
                    st.session_state["analysis_data"] = {
                        "upload_data": upload_data,
                        "diagnostics": diagnostics,
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
                    # Safely parse JSON error message, fallback to raw text if it fails
                    try:
                        err_msg = e.response.json().get("detail", str(e))
                    except Exception:
                        err_msg = str(e)
                    st.error(f"🚨 API Error: {err_msg}")
                    st.stop()

        # Render data directly from the cache
        data = st.session_state["analysis_data"]
        upload_data = data["upload_data"]
        diagnostics = data["diagnostics"]

        # Show basic info in the sidebar
        st.sidebar.success("✅ File successfully processed")
        st.sidebar.info(
            f"**DB:** {upload_data['db_name']}\n\n"
            f"**Elapsed Time:** {upload_data['elapsed_mins']} min"
        )

        # 3. Render Executive Dashboard
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

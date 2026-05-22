"""
Streamlit Web Interface for AWR Expert.
Consumes the FastAPI backend to render an Executive Dashboard.
"""

import requests
import streamlit as st

# API Server Configuration
API_URL = "http://127.0.0.1:8000"

# Page Configuration
st.set_page_config(page_title="AWR Expert", page_icon="🧠", layout="wide")

st.title("🧠 AWR Expert: Executive Dashboard")
st.markdown("Heuristic Intelligence for Oracle Databases")

# Sidebar for file upload
with st.sidebar:
    st.header("⚙️ AWR Ingestion")
    uploaded_file = st.file_uploader("Upload your AWR report (HTML)", type=["html"])

if uploaded_file:
    with st.spinner("Analyzing report with heuristic engine..."):
        # 1. Send the file to the FastAPI backend
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/html")}
        try:
            upload_res = requests.post(f"{API_URL}/upload", files=files)
            upload_res.raise_for_status()
            upload_data = upload_res.json()
            awr_hash = upload_data["awr_hash"]

            # Show basic info in the sidebar
            st.sidebar.success("✅ File successfully processed")
            st.sidebar.info(
                f"**DB:** {upload_data['db_name']}\n\n"
                f"**Elapsed Time:** {upload_data['elapsed_mins']} min"
            )

            # 2. Query diagnostics
            analysis_res = requests.get(f"{API_URL}/analyze/{awr_hash}")
            analysis_res.raise_for_status()
            diagnostics = analysis_res.json()["diagnostics"]

            # 3. Render Executive Dashboard
            st.header("📊 Overall Health Score")

            if not diagnostics:
                st.success(
                    "✨ All good! No critical bottlenecks detected. The database is healthy."
                )
            else:
                for diag in diagnostics:
                    # Determine colors and UI components based on severity
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

                        # Create a two-column layout
                        col1, col2 = st.columns([1, 3])

                        with col1:
                            st.metric(label="Status", value=diag["status"])
                            st.metric(label="Impact", value=diag["impact"])

                        with col2:
                            msg_type(f"**Recommendation:** {diag['recommendation']}")

                            # "Skeptical DBA" Mode: Hide raw data in an expander
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

        except requests.exceptions.ConnectionError:
            st.error(
                "🚨 Connection error. Ensure your FastAPI server is running on port 8000."
            )
        except requests.exceptions.HTTPError as e:
            st.error(f"🚨 API Error: {e.response.json().get('detail', str(e))}")

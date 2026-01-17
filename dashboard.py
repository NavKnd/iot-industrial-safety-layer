import streamlit as st
import requests
import pandas as pd

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="IoT Industrial Safety Dashboard",
    layout="wide",
)

st.title(" IoT Industrial Safety Dashboard")
st.caption("Live monitoring and analytics for industrial safety alerts")

# ---------------- API URLS ----------------
BASE_API = "https://iot-industrial-safety-layer.onrender.com"

ACTIVE_API = f"{BASE_API}/alerts"
HISTORY_API = f"{BASE_API}/alerts/history"
SENSOR_API = f"{BASE_API}/all-data"


# ---------------- FETCH FUNCTION ----------------
def fetch_data(url):
    try:
        r = requests.get(url)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return []

# ---------------- FETCH DATA ----------------
active_alerts = fetch_data(ACTIVE_API)
history_alerts = fetch_data(HISTORY_API)
sensor_data = fetch_data(SENSOR_API)

df = pd.DataFrame(history_alerts)
sensor_df = pd.DataFrame(sensor_data)

# ---------------- SIDEBAR FILTERS ----------------
st.sidebar.header(" Filters")

if not df.empty:
    severity_filter = st.sidebar.multiselect(
        "Severity",
        options=df["severity"].unique().tolist(),
        default=df["severity"].unique().tolist(),
    )
    df = df[df["severity"].isin(severity_filter)]

# ---------------- KPI METRICS ----------------
col1, col2, col3 = st.columns(3)

col1.metric(" Active Alerts", len(active_alerts))
col2.metric(" Total Alerts", len(df))
col3.metric(
    " Critical Alerts",
    len(df[df["severity"] == "HIGH"]) if not df.empty else 0
)

# ---------------- TABS ----------------
tab1, tab2, tab3 = st.tabs([" Overview", " History", " Analytics"])

# ---------------- TAB 1: OVERVIEW ----------------
with tab1:
    st.subheader(" Active Alerts")

    if len(active_alerts) == 0:
        st.success("System is SAFE  No active alerts.")
    else:
        for alert in active_alerts:
            severity = alert.get("severity", "LOW")

            msg = (
                f"**{alert['alert_type']}** | `{alert['device_id']}`\n\n"
                f"{alert['message']}\n\n"
                f" {alert['created_at']}"
            )

            if severity == "HIGH":
                st.error(msg)
            elif severity == "MEDIUM":
                st.warning(msg)
            else:
                st.info(msg)

# ---------------- TAB 2: HISTORY ----------------
with tab2:
    st.subheader(" Alert History")

    if df.empty:
        st.info("No alert history available.")
    else:
        st.dataframe(df, use_container_width=True)

# ---------------- TAB 3: ANALYTICS ----------------
with tab3:
    if df.empty:
        st.info("No data available for analytics.")
    else:
        # ---- Alerts by Type ----
        st.subheader(" Alerts by Type")
        st.bar_chart(df["alert_type"].value_counts())

        # ---- Alerts by Severity ----
        st.subheader(" Alerts by Severity")
        st.bar_chart(df["severity"].value_counts())

        # ---- Anomaly Frequency (USING REAL ALERT TYPES) ----
        st.subheader(" Anomaly Alerts Frequency")
        anomaly_df = df[df["alert_type"].isin(["HIGH_GAS", "HIGH_TEMP", "LOW_TEMP"])]

        if not anomaly_df.empty:
            st.bar_chart(anomaly_df["alert_type"].value_counts())
        else:
            st.info("No anomaly alerts detected yet.")

        # ---- Sensor Trends ----
        st.subheader(" Sensor Value Trends")

        if not sensor_df.empty:
            sensor_df["timestamp"] = pd.to_datetime(sensor_df["timestamp"])
            sensor_df = sensor_df.sort_values("timestamp")

            st.line_chart(
                sensor_df.set_index("timestamp")[["temperature", "gas_level"]]
            )
        else:
            st.info("No sensor data available for trend analysis.")

st.subheader(" Sensor-wise Trends")

if not sensor_df.empty:
    sensor_df["timestamp"] = pd.to_datetime(sensor_df["timestamp"])

    # Device selector
    device_list = sensor_df["device_id"].unique().tolist()
    selected_device = st.selectbox(
        "Select Device",
        device_list
    )

    device_df = sensor_df[sensor_df["device_id"] == selected_device]
    device_df = device_df.sort_values("timestamp")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("###  Temperature Trend")
        st.line_chart(
            device_df.set_index("timestamp")[["temperature"]]
        )

    with col2:
        st.markdown("###  Gas Level Trend")
        st.line_chart(
            device_df.set_index("timestamp")[["gas_level"]]
        )

else:
    st.info("No sensor data available.")

st.subheader(" Alerts Frequency per Device")

device_alerts = df["device_id"].value_counts()

st.bar_chart(device_alerts)

st.subheader(" Device vs Severity Heatmap")

pivot = df.pivot_table(
    index="device_id",
    columns="severity",
    values="id",
    aggfunc="count",
    fill_value=0
)

st.dataframe(pivot)

st.subheader(" Alert Resolution Time Analysis")

resolved_df = df[df["resolved_at"].notna()].copy()

if resolved_df.empty:
    st.info("No resolved alerts available.")
else:
    resolved_df["created_at"] = pd.to_datetime(resolved_df["created_at"])
    resolved_df["resolved_at"] = pd.to_datetime(resolved_df["resolved_at"])

    resolved_df["resolution_time_sec"] = (
        resolved_df["resolved_at"] - resolved_df["created_at"]
    ).dt.total_seconds()

    st.metric(
        "Average Resolution Time (sec)",
        round(resolved_df["resolution_time_sec"].mean(), 2)
    )

    st.line_chart(
        resolved_df.set_index("created_at")["resolution_time_sec"]
    )

st.subheader(" Device Health Score")

def health_score(device_df):
    score = 100
    score -= len(device_df[device_df["severity"] == "HIGH"]) * 20
    score -= len(device_df[device_df["severity"] == "MEDIUM"]) * 10
    score -= len(device_df[device_df["severity"] == "LOW"]) * 5
    return max(score, 0)

health_scores = (
    df.groupby("device_id")
    .apply(health_score)
    .sort_values()
)

st.bar_chart(health_scores)

st.download_button(
    "⬇ Download Alert History (CSV)",
    df.to_csv(index=False),
    file_name="alert_history.csv",
    mime="text/csv"
)




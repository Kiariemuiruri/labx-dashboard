import streamlit as st
import pandas as pd
import gspread
import json
import os
from google.oauth2.service_account import Credentials
import plotly.express as px
import streamlit_authenticator as stauth
from datetime import datetime
import yaml
from yaml.loader import SafeLoader

# =========================
# Page Config
# =========================
st.set_page_config(page_title="LabX Dashboard", layout="wide", initial_sidebar_state="expanded")

# =========================
# Professional Custom CSS
# =========================
st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(135deg, #4B0082, #1E90FF);
            color: #EAEAEA;
            font-family: 'Segoe UI', sans-serif;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        [data-testid="stSidebar"] {
            background-color: rgba(30,144,255,0.3);
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.5);
            color: #FFFFFF;
            width: 25vw;
            min-width: 250px;
        }
        .stHeader {
            font-size: 28px;
            font-weight: bold;
            color: #FFFFFF;
        }
        .stSubheader {
            font-size: 20px;
            color: #D3D3D3;
        }
        .stMetric {
            background-color: rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 12px;
            text-align: center;
            color: #FFFFFF;
        }
        .stChart {
            background-color: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 15px;
        }
        .stDataFrame {
            background-color: rgba(255,255,255,0.05);
            border-radius: 10px;
            padding: 10px;
            color: #EAEAEA;
        }
        button {
            background-color: #1E90FF;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: 500;
        }
        button:hover {
            background-color: #104E8B;
            color: #FFFFFF;
        }
        /* Responsive date picker styling */
        .stDateInput > div > div {
            min-width: 90% !important;
            max-height: 400px !important;
            overflow-y: auto;
            background-color: rgba(0,0,0,0.8) !important;
            border-radius: 10px;
            padding: 10px;
        }
        .stDateInput > div > div > div {
            color: #FFFFFF !important;
            font-size: 14px;
        }
        .stDateInput [data-baseweb="select"] {
            width: 90% !important;
        }
        .stDateInput .css-1v0mbdj {
            max-height: 350px !important;
            overflow-y: auto;
            width: 100% !important;
        }
        .stDateInput .css-1cpxx8g {
            width: 100% !important;
            max-width: 90% !important;
        }
        .stDateInput .react-datepicker {
            width: 100% !important;
            background-color: rgba(0,0,0,0.8) !important;
            border: none !important;
            color: #FFFFFF !important;
        }
        .stDateInput .react-datepicker__header {
            background-color: #1E90FF;
            color: #FFFFFF !important;
            border-bottom: 1px solid #D3D3D3;
        }
        .stDateInput .react-datepicker__navigation {
            background-color: #4B0082 !important;
            border: none !important;
        }
        .stDateInput .react-datepicker__day-name {
            color: #D3D3D3 !important;
        }
        .stDateInput .react-datepicker__day {
            color: #EAEAEA !important;
        }
        .stDateInput .react-datepicker__day--selected {
            background-color: #1E90FF !important;
            color: #FFFFFF !important;
        }
        /* Enhanced greeting styling */
        [data-testid="stSidebar"] h3 {
            font-size: 28px !important;
            font-weight: bold !important;
            color: #FFFFFF !important;
            margin-bottom: 20px !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# Authentication Setup
# =========================
# Check if running on Render
is_render = os.getenv("RENDER") == "true"

# Load config.yaml (local file or env var)
if is_render:
    config_yaml = os.getenv("CONFIG_YAML")
    if not config_yaml:
        st.error("CONFIG_YAML environment variable is missing on Render. Expected YAML content for authentication.")
        st.stop()
    try:
        config = yaml.load("config.yaml", Loader=SafeLoader)
        if not config:
            raise ValueError("Parsed YAML is empty.")
    except yaml.YAMLError as e:
        st.error(f"Invalid YAML in CONFIG_YAML: {str(e)}. Check your YAML content in Render environment variables.")
        st.stop()
    except Exception as e:
        st.error(f"Error parsing CONFIG_YAML: {str(e)}.")
        st.stop()
else:
    try:
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        if not config:
            raise ValueError("config.yaml is empty.")
    except FileNotFoundError:
        st.error("config.yaml not found in project root. Please create it with credentials, cookie, and preauthorized keys.")
        st.stop()
    except yaml.YAMLError as e:
        st.error(f"Invalid YAML in config.yaml: {str(e)}.")
        st.stop()
    except Exception as e:
        st.error(f"Error reading config.yaml: {str(e)}.")
        st.stop()

# Validate config structure
creds_dict = config.get("credentials", {})
cookie_config = config.get("cookie", {})
preauthorized = config.get("preauthorized", [])
if "usernames" not in creds_dict:
    st.error("config.yaml missing 'credentials.usernames' key. Expected format: credentials: {usernames: {...}}")
    st.stop()

cookie_name = cookie_config.get("name", "labx_cookie")
cookie_key = cookie_config.get("key", "default_key")
if cookie_key == "default_key":
    st.warning("Using default cookie key. Set a strong random key in config.yaml for security.")
cookie_expiry_days = float(cookie_config.get("expiry_days", 30))

# Initialize authenticator with auto_hash=False (assuming pre-hashed passwords)
try:
    authenticator = stauth.Authenticate(
        creds_dict,
        cookie_name,
        cookie_key,
        cookie_expiry_days,
        preauthorized,
        auto_hash=False  # Use False for pre-hashed passwords
    )

    # Render login module
    if st.session_state.get("authentication_status") is None:
        st.markdown('<div class="main">', unsafe_allow_html=True)
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("<h2>🔐 LabX</h2>", unsafe_allow_html=True)
        
        login_result = authenticator.login(
            location='main',
            fields={
                'Form name': 'Login',
                'Username': 'Username',
                'Password': 'Password',
                'Login': 'Login'
            }
        )
        
        st.markdown("</div></div>", unsafe_allow_html=True)
        if login_result:
            name, authentication_status, username = login_result
            st.session_state["authentication_status"] = authentication_status
            st.session_state["name"] = name
            st.session_state["username"] = username
            if authentication_status:
                st.rerun()

    authentication_status = st.session_state.get("authentication_status")
    name = st.session_state.get("name")
    username = st.session_state.get("username")

except KeyError as e:
    st.error(f"KeyError in Authenticate: Missing key '{str(e)}' in credentials. Ensure 'usernames' exists with user data.")
    st.stop()
except Exception as e:
    st.error(f"Authentication setup error: {str(e)}. Verify streamlit-authenticator==0.4.2 and Streamlit>=1.30.0. Config keys: {list(config.keys()) if 'config' in locals() else 'N/A'}")
    authentication_status = False

# =========================
# Dynamic Greeting
# =========================
current_time = datetime.now().hour
if current_time < 12:
    greeting = "Good Morning"
elif 12 <= current_time < 16:
    greeting = "Good Afternoon"
else:
    greeting = "Good Evening"

# =========================
# Authenticated Dashboard
# =========================
if authentication_status:
    st.sidebar.markdown("LabX Dashboard")
    logout_result = authenticator.logout('Logout', 'sidebar')
    if logout_result:
        st.rerun()  # Forces UI refresh after logout
    st.header(f"{greeting} {name}")

    # ------------------------- 
    # Google Sheets setup
    # ------------------------- 
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    # Load Google Sheets credentials (local file or env var)
    if is_render:
        google_creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
        if not google_creds_json:
            st.error("GOOGLE_SHEETS_CREDENTIALS environment variable is missing on Render. Expected JSON content for Google Service Account.")
            st.stop()
        try:
            google_creds = json.loads('credentials.json')
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON in GOOGLE_SHEETS_CREDENTIALS: {str(e)}. Check your JSON content in Render environment variables.")
            st.stop()
    else:
        try:
            with open("credentials.json", "r") as f:
                google_creds = json.load(f)
        except FileNotFoundError:
            st.error("credentials.json not found in project root. Please create it with Google Service Account credentials.")
            st.stop()
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON in credentials.json: {str(e)}.")
            st.stop()
        except Exception as e:
            st.error(f"Error reading credentials.json: {str(e)}.")
            st.stop()

    # Create credentials
    creds = Credentials.from_service_account_info(google_creds, scopes=SCOPES)

    gc = gspread.authorize(creds)
    sheet = gc.open("Microfinance Leads").sheet1

    # ------------------------- 
    # Load Data
    # ------------------------- 
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], format='ISO8601')
    df['Score'] = pd.to_numeric(df['Score'], errors='coerce')

    # ------------------------- 
    # Filters
    # ------------------------- 
    st.sidebar.subheader("Filter Options")
    with st.sidebar.expander("Date & Score", expanded=False):
        today = pd.to_datetime('today').date()
        default_min_date = df['Timestamp'].min().date() if not df.empty else today
        default_max_date = min(df['Timestamp'].max().date(), today) if not df.empty else today
        date_range = st.date_input("Date Range", [default_min_date, default_max_date], max_value=today)
        min_score, max_score = st.slider("Score Range", 0.0, 5.0, (0.0, 5.0))

    with st.sidebar.expander("Vehicle Type", expanded=False):
        vehicle_types = st.multiselect("Vehicle Types", options=df['Vehicle Type'].unique(), default=df['Vehicle Type'].unique())

    # Handle single date or range
    start_date = date_range[0] if isinstance(date_range, (list, tuple)) and len(date_range) > 0 else date_range
    end_date = date_range[-1] if isinstance(date_range, (list, tuple)) and len(date_range) > 1 else date_range

    mask = (
        (df['Timestamp'].dt.date >= start_date) &
        (df['Timestamp'].dt.date <= end_date) &
        (df['Score'].between(min_score, max_score)) &
        (df['Vehicle Type'].isin(vehicle_types))
    )
    filtered_df = df[mask].copy()

    # ------------------------- 
    # KPIs
    # ------------------------- 
    total_leads = len(filtered_df)
    completion_rate = (filtered_df['Score'].notna().sum() / total_leads) * 100 if total_leads > 0 else 0
    avg_score = filtered_df['Score'].mean()
    high_quality = (filtered_df['Score'] > 3).sum() / total_leads * 100 if total_leads > 0 else 0

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Leads", total_leads)
        st.metric("Avg. Lead Score", f"{avg_score:.1f}/5")
    with col2:
        st.metric("Completion Rate", f"{completion_rate:.1f}%")
        st.metric("High-Quality Leads", f"{high_quality:.1f}%")

    # ------------------------- 
    # Chart Palette (White & Gray)
    # ------------------------- 
    palette = ["#FFFFFF", "#D3D3D3", "#A9A9A9", "#808080"]

    # ------------------------- 
    # Hourly Leads (Smoothed Line Graph)
    # ------------------------- 
    st.subheader("Hourly Leads")
    filtered_df['Hour'] = filtered_df['Timestamp'].dt.hour
    hourly_counts = filtered_df.groupby('Hour').size().reindex(range(24), fill_value=0).reset_index(name='Count')
    hourly_counts['Hour'] = hourly_counts['Hour'].astype(int)
    # Apply 3-hour rolling average for smoothing
    hourly_counts['Smoothed Count'] = hourly_counts['Count'].rolling(window=3, center=True, min_periods=1).mean()
    fig4 = px.line(
        hourly_counts, x="Hour", y="Smoothed Count", markers=True,
        color_discrete_sequence=["#FFFFFF"]
    )
    fig4.update_traces(hovertemplate="Hour: %{x}:00<br>Count: %{y:.2f}")
    fig4.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Segoe UI", size=14, color="#FFFFFF"),
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.2)", tickvals=list(range(24)), ticktext=[f"{h}:00" for h in range(24)]),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.2)")
    )
    st.plotly_chart(fig4, use_container_width=True)

    # ------------------------- 
    # Leads Over Time
    # ------------------------- 
    st.subheader("Leads Over Time")
    leads_over_time = filtered_df.set_index('Timestamp').resample('D')['Score'].count().reset_index()
    leads_over_time.columns = ['Timestamp', 'Leads']
    fig3 = px.line(
        leads_over_time, x='Timestamp', y='Leads', markers=True,
        color_discrete_sequence=["#FFFFFF"]
    )
    fig3.update_traces(hovertemplate="Date: %{x}<br>Leads: %{y}")
    fig3.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Segoe UI", size=14, color="#FFFFFF"),
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.2)"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.2)")
    )
    st.plotly_chart(fig3, use_container_width=True)

    # ------------------------- 
    # Lead Scores Distribution
    # ------------------------- 
    st.subheader("Lead Scores Distribution")
    score_counts = filtered_df['Score'].value_counts().sort_index().reset_index()
    score_counts.columns = ['Score', 'Count']
    fig1 = px.bar(
        score_counts, x="Score", y="Count", text="Count",
        color="Score", color_discrete_sequence=palette
    )
    fig1.update_traces(textposition="outside", hovertemplate="Score: %{x}<br>Count: %{y}")
    fig1.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Segoe UI", size=14, color="#FFFFFF"),
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.2)"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.2)")
    )
    st.plotly_chart(fig1, use_container_width=True)

    # ------------------------- 
    # Vehicle Type Breakdown
    # ------------------------- 
    st.subheader("Vehicle Type Breakdown")
    vehicle_counts = filtered_df['Vehicle Type'].value_counts().reset_index()
    vehicle_counts.columns = ["Vehicle Type", "Count"]
    fig2 = px.bar(
        vehicle_counts, x="Vehicle Type", y="Count", text="Count",
        color="Vehicle Type", color_discrete_sequence=palette
    )
    fig2.update_traces(textposition="outside", hovertemplate="Vehicle: %{x}<br>Count: %{y}")
    fig2.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Segoe UI", size= 14, color="#FFFFFF"),
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.2)"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.2)")
    )
    st.plotly_chart(fig2, use_container_width=True)

elif authentication_status is False:
    st.error('Username/password is incorrect')
elif authentication_status is None:
    st.warning('Please enter your username and password')
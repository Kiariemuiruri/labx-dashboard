import streamlit as st
import pandas as pd
import gspread, json, copy, base64
from google.oauth2.service_account import Credentials
import plotly.express as px
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
from datetime import datetime
import os, io
from fpdf import FPDF

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
        .block-container {
            padding-top: 0.5rem !important;  /* default is ~6rem */
            padding-bottom: 0rem !important;
        }
        .css-1aumxhk { /* Header */
        display: none;
    }
    .st-emotion-cache-gquqoo {
        background: linear-gradient(to right, #3B82F6, #9333EA) !important;
        margin: 0;
        padding: 0;
        height: 100vh;
        width: 100vw;
        overflow: hidden;
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

# --- Load credentials and cookie settings from Render environment variables ---
credentials = {
    "usernames": {
        os.getenv("AUTH_USER_NAME"): {
            "name": os.getenv("AUTH_USER_NAME"),
            "email": os.getenv("AUTH_USER_EMAIL"),
            "password": os.getenv("AUTH_USER_HASHED_PASSWORD"),
        }
    }
}

cookie_name = os.getenv("AUTH_COOKIE_NAME", "app_cookie")
cookie_key = os.getenv("AUTH_COOKIE_KEY", "default_key")
cookie_expiry_days = int(os.getenv("AUTH_COOKIE_EXPIRY_DAYS", "30"))

# --- Initialize authenticator ---
try:
    authenticator = stauth.Authenticate(
        credentials,
        cookie_name,
        cookie_key,
        cookie_expiry_days
    )
    # Render login module
   # name, authentication_status, username = authenticator.login("Login", "main")

    if st.session_state.get("authentication_status") is None:
        st.markdown('<div class="main">', unsafe_allow_html=True)
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("<h2>LabX</h2>", unsafe_allow_html=True)
        
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

except Exception as e:
    st.error(f"Authentication error: {str(e)}. Please update Streamlit to version 1.30.0 or higher and ensure compatibility with streamlit_authenticator 0.4.2.")
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
    # Function to create the dashboard PDF (excluding sidebar)
    def create_dashboard_pdf(df, name):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", "B", 16)
        pdf.set_text_color(255, 255, 255)
        pdf.set_fill_color(30, 144, 255)
        pdf.cell(0, 10, "LabX Dashboard Report", 0, 1, "C", fill=True)

        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, f"Generated for: {name}", 0, 1)
        pdf.cell(0, 10, f"Total Leads: {len(df)}", 0, 1)
        pdf.cell(0, 10, f"Average Score: {df['Score'].mean():.2f}", 0, 1)
        pdf.cell(0, 10, f"Date Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 1)

        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Top 10 Recent Leads", 0, 1)

        pdf.set_font("Arial", "", 10)
        for i, row in df.head(10).iterrows():
            pdf.cell(0, 8, f"{row.get('Name', 'N/A')} - {row.get('Vehicle Type', 'N/A')} - {row.get('Score', 'N/A')}", 0, 1)

        # Return the PDF as a bytes buffer
        pdf_output = pdf.output(dest="S").encode("latin1")
        pdf_buffer = io.BytesIO(pdf_output)
        return pdf_buffer


    st.sidebar.markdown(f"{greeting}, {name}")
    logout_result = authenticator.logout('Logout', 'sidebar')
    if logout_result:
        st.rerun()  # Forces UI refresh after logout
    st.header(f"Dashboard")


    # ------------------------- 
    # Google Sheets setup
    # ------------------------- 
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
   # Load and decode Base64 credentials
    b64_creds = os.getenv("GOOGLE_CREDENTIALS_B64")
    if not b64_creds:
        raise ValueError("Missing GOOGLE_CREDENTIALS_B64 environment variable")

    decoded = base64.b64decode(b64_creds).decode()
    google_creds = json.loads(decoded)

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

    # Create PDF bytes
    pdf_buffer = create_dashboard_pdf(filtered_df, name)
    b64_pdf = base64.b64encode(pdf_buffer.read()).decode('utf-8')
    # Render icon button at top right
    download_icon_html = f"""
        <div style='position: fixed; top: 15px; right: 25px; z-index: 999;'>
            <a href="data:application/octet-stream;base64,{b64_pdf}" download="LabX_Dashboard.pdf"
            style="background-color:#1E90FF; padding:10px 12px; border-radius:50%; text-decoration:none;
                    box-shadow:0 0 10px rgba(0,0,0,0.3);">
                <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="white" viewBox="0 0 16 16">
                    <path d="M.5 9.9a.5.5 0 0 1 .5.5V13a1 1 0 0 0 1 1h12a1
                            1 0 0 0 1-1V10.4a.5.5 0 0 1 1 0V13a2 2
                            0 0 1-2 2H2a2 2 0 0 1-2-2V10.4a.5.5 0 0 1
                            .5-.5z"/>
                    <path d="M7.646 10.854a.5.5 0 0 0 .708 0l3-3a.5.5 0
                            0 0-.708-.708L8.5 9.293V1.5a.5.5 0 0
                            0-1 0v7.793L5.354 7.146a.5.5 0 1
                            0-.708.708l3 3z"/>
                </svg>
            </a>
        </div>
    """
    st.markdown(download_icon_html, unsafe_allow_html=True)
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
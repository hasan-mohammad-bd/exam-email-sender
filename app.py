"""Main Streamlit Application - Exam Portal Email Sender"""

import streamlit as st
import pandas as pd
from datetime import datetime, time as dt_time
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Page configuration — must be the very first Streamlit command
st.set_page_config(
    page_title="Exam Portal Email Sender",
    page_icon="📧",
    layout="wide"
)

from modules.file_handler import FileHandler
from modules.api_client import APIClient
from modules.email_sender import EmailSender
from modules.template_manager import TemplateManager
from modules.calendar_event import CalendarEvent
from config.settings import Config
from modules.visual_editor import visual_editor
from modules.email_tracking import EmailTracker

# Custom CSS
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
    }
    .success-box {
        padding: 15px;
        border-radius: 5px;
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        margin: 10px 0;
    }
    .error-box {
        padding: 15px;
        border-radius: 5px;
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        margin: 10px 0;
    }
    .info-box {
        padding: 15px;
        border-radius: 5px;
        background-color: #d1ecf1;
        border-left: 4px solid #17a2b8;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


# ─── Initialize session state ───────────────────────────────────────────────
def init_session_state():
    defaults = {
        'students': [],
        'students_with_links': [],
        'failed_candidates': [],
        'links_generated': False,
        'emails_sent': False,
        'email_results': [],
        'file_errors': [],
        'email_template': TemplateManager.get_default_template(),
        'email_subject': 'Assessment Link & Login Credentials | TAM – Digital Banking | 28 February',
        'program_id': int(Config.DEFAULT_PROGRAM_ID) if Config.DEFAULT_PROGRAM_ID else 1,
        'round_id': int(Config.DEFAULT_ROUND_ID) if Config.DEFAULT_ROUND_ID else 1,
        'session_time': Config.DEFAULT_SESSION_TIME or '730h',
        'custom_program_name': '',
        'sender_email': Config.SENDER_EMAIL,
        'sender_name': Config.SENDER_NAME,
        'aws_access_key': Config.AWS_SES_ACCESS_KEY,
        'aws_secret_key': Config.AWS_SES_SECRET_KEY,
        'aws_region': Config.AWS_SES_REGION,
        'api_endpoint': Config.API_ENDPOINT,
        'api_key': Config.API_KEY,
        # Calendar event options
        'include_calendar_event': False,
        'calendar_event_type': CalendarEvent.EVENT_TYPE_GOOGLE,
        'calendar_event_title': '',
        'calendar_event_date': None,
        'calendar_event_start_time': dt_time(9, 0),
        'calendar_event_duration': '1 hour',
        'calendar_event_duration_hours': 1,
        'calendar_event_duration_minutes': 0,
        'calendar_event_organizer_name': '',
        'calendar_event_organizer_email': '',
        'calendar_event_location': '',
        'calendar_event_meeting_link': '',
        'calendar_event_description': '',
        # Email mode - skip link generation
        'skip_link_generation': False,
        # Visual editor state
        'visual_editor_active': False,
        'template_editor_key': 0,
        'loaded_template_filename': None,
        # Manual input rows
        'manual_entry_rows': [{'name': '', 'email': '', 'login_id': '', 'password': ''}],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()

# ─── Header ─────────────────────────────────────────────────────────────────
st.title("📧 Exam Portal Email Sender")
st.markdown("Automated tool for generating exam links and sending personalized emails to students.")

# ─── Email Mode Toggle ──────────────────────────────────────────────────────
skip_link_generation = st.toggle(
    "📨 General Email Mode (send without generating login links)",
    value=st.session_state.skip_link_generation,
    help="Enable this to send emails directly to uploaded students without generating exam portal login links. "
         "Useful for sending general announcements, reminders, or custom emails.",
)
st.session_state.skip_link_generation = skip_link_generation

if skip_link_generation:
    st.info("ℹ️ **General Email Mode** — Login link generation will be skipped. "
            "You can send emails directly after uploading data and setting up the template. "
            "Placeholders like `{login_link}`, `{candidate_id}`, `{round_name}`, and `{expires_at}` will be empty.")

st.markdown("---")

# ─── Create tabs ─────────────────────────────────────────────────────────────
if skip_link_generation:
    tab1, tab2, tab4, tab5, tab6, tab7 = st.tabs([
        "1️⃣ Email Settings",
        "2️⃣ Upload Data",
        "3️⃣ Email Template",
        "4️⃣ Send Emails",
        "5️⃣ Reports",
        "6️⃣ Email Tracking"
    ])
    tab3 = None  # No generate links tab
else:
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "1️⃣ API Parameters",
        "2️⃣ Upload Data",
        "3️⃣ Generate Links",
        "4️⃣ Email Template",
        "5️⃣ Send Emails",
        "6️⃣ Reports",
        "7️⃣ Email Tracking"
    ])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: API Parameters
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("Step 1: Configure API Parameters")
    st.markdown("Set the parameters needed for the API to generate unique exam links.")

    col1, col2 = st.columns(2)

    with col1:
        api_endpoint = st.text_input(
            "API Endpoint URL *",
            value=st.session_state.api_endpoint,
            help="The URL for the link generation API"
        )
        st.session_state.api_endpoint = api_endpoint

        program_id = st.number_input(
            "Program ID *",
            min_value=1,
            value=st.session_state.program_id,
            help="The program ID for link generation"
        )
        st.session_state.program_id = program_id

    with col2:
        round_id = st.number_input(
            "Round ID *",
            min_value=1,
            value=st.session_state.round_id,
            help="The round ID for link generation"
        )
        st.session_state.round_id = round_id

        session_time = st.text_input(
            "Session Time *",
            value=st.session_state.session_time,
            help="Duration the link remains valid (e.g., 730h)"
        )
        st.session_state.session_time = session_time

        api_key = st.text_input(
            "API Key *",
            value=st.session_state.api_key,
            type="password",
            help="API key for authentication"
        )
        st.session_state.api_key = api_key

    st.markdown("---")
    st.subheader("📧 AWS SES Email Configuration")
    st.markdown("Configure your AWS SES credentials for sending emails.")

    col3, col4 = st.columns(2)

    with col3:
        aws_access_key = st.text_input(
            "AWS SES Access Key *",
            value=st.session_state.aws_access_key,
            type="password",
            help="AWS IAM access key with SES permissions"
        )
        st.session_state.aws_access_key = aws_access_key

        aws_secret_key = st.text_input(
            "AWS SES Secret Key *",
            value=st.session_state.aws_secret_key,
            type="password",
            help="AWS IAM secret key"
        )
        st.session_state.aws_secret_key = aws_secret_key

        aws_region = st.text_input(
            "AWS Region",
            value=st.session_state.aws_region,
            help="e.g., ap-south-1, us-east-1"
        )
        st.session_state.aws_region = aws_region

    with col4:
        sender_email = st.text_input(
            "Sender Email *",
            value=st.session_state.sender_email,
            help="Verified SES sender email (e.g., noreply_gr@ppl.how)"
        )
        st.session_state.sender_email = sender_email

        sender_name = st.text_input(
            "Sender Name",
            value=st.session_state.sender_name,
            help="Name displayed as the sender"
        )
        st.session_state.sender_name = sender_name

    # Test AWS SES connection
    if st.button("🔌 Test AWS SES Connection"):
        if not aws_access_key or not aws_secret_key:
            st.error("Please enter your AWS access key and secret key first.")
        else:
            ses_config = {
                'aws_access_key': aws_access_key,
                'aws_secret_key': aws_secret_key,
                'aws_region': aws_region,
                'sender_email': sender_email,
                'sender_name': sender_name,
                'configuration_set': Config.AWS_SES_CONFIGURATION_SET,
            }
            with st.spinner("Testing AWS SES connection..."):
                email_sender = EmailSender(ses_config)
                success, message = email_sender.test_connection()

            if success:
                st.success(f"✅ {message}")
            else:
                st.error(f"❌ {message}")

    # Summary
    st.markdown("---")
    st.subheader("📋 Current Configuration Summary")
    config_col1, config_col2 = st.columns(2)
    with config_col1:
        st.markdown(f"- **API Endpoint:** `{api_endpoint}`")
        st.markdown(f"- **Program ID:** `{program_id}`")
        st.markdown(f"- **Round ID:** `{round_id}`")
        st.markdown(f"- **Session Time:** `{session_time}`")
    with config_col2:
        st.markdown(f"- **AWS Region:** `{aws_region}`")
        st.markdown(f"- **Sender:** `{sender_name}` <`{sender_email}`>")
        st.markdown(f"- **Access Key:** `{'*' * 8 + aws_access_key[-4:] if len(aws_access_key) > 4 else 'Not set'}`")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: Upload Data
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.header("Step 2: Upload Student Data")
    st.markdown("Upload a file or enter student details manually.")

    input_method = st.radio(
        "Choose input method:",
        ["📁 Upload File", "✏️ Manual Input"],
        horizontal=True,
        key="input_method"
    )

    if input_method == "📁 Upload File":
        # Sample data download
        with st.expander("📥 Download Sample File"):
            sample_df = pd.DataFrame({
                'Name': ['Alice Smith', 'Bob Johnson', 'Charlie Brown'],
                'Email': ['alice@example.com', 'bob@example.com', 'charlie@example.com']
            })
            csv_data = sample_df.to_csv(index=False)
            st.download_button(
                label="Download Sample CSV",
                data=csv_data,
                file_name="sample_students.csv",
                mime="text/csv"
            )
            st.dataframe(sample_df, use_container_width=True)

        uploaded_file = st.file_uploader(
            "Choose a CSV or Excel file",
            type=['csv', 'xlsx', 'xls'],
            help="File must have 'Name' and 'Email' columns. Optionally include Login ID and Password columns."
        )

        if uploaded_file is not None:
            # Read file columns for optional mapping
            uploaded_file.seek(0)
            file_columns = FileHandler.get_file_columns(uploaded_file)
            uploaded_file.seek(0)

            # Optional login_id and password column pickers
            none_option = '— None —'
            col_opt1, col_opt2 = st.columns(2)
            with col_opt1:
                login_id_col = st.selectbox(
                    "Login ID Column (optional)",
                    options=[none_option] + file_columns,
                    index=0,
                    help="Select the column that contains Login IDs. Leave as '— None —' to skip.",
                    key="file_login_id_col",
                )
            with col_opt2:
                password_col = st.selectbox(
                    "Password Column (optional)",
                    options=[none_option] + file_columns,
                    index=0,
                    help="Select the column that contains Passwords. Leave as '— None —' to skip.",
                    key="file_password_col",
                )

            selected_login_id_col = '' if login_id_col == none_option else login_id_col
            selected_password_col = '' if password_col == none_option else password_col

            with st.spinner("Processing file..."):
                students, errors = FileHandler.process_file(
                    uploaded_file,
                    login_id_column=selected_login_id_col,
                    password_column=selected_password_col,
                )

            # Show errors
            if errors:
                with st.expander(f"⚠️ {len(errors)} Warning(s)/Error(s) Found", expanded=True):
                    for error in errors:
                        st.warning(error)

            # Show valid students
            if students:
                st.session_state.students = students
                st.session_state.file_errors = errors

                st.success(f"✅ Successfully loaded **{len(students)}** valid student(s)")

                # Preview
                preview_df = pd.DataFrame(students)
                st.dataframe(preview_df, use_container_width=True, height=300)

                # Stats
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Valid Students", len(students))
                with col2:
                    st.metric("Warnings/Errors", len(errors))
                with col3:
                    unique_domains = len(set(s['email'].split('@')[1] for s in students))
                    st.metric("Unique Email Domains", unique_domains)
            else:
                st.error("No valid students found in the uploaded file.")

    else:
        # ── Manual Input ────────────────────────────────────────────────────
        st.markdown("Enter student **Name** and **Email** below. **Login ID** and **Password** are optional. Click ➕ to add more rows.")

        # ── Quick Search from User Data ─────────────────────────────────────
        user_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'user-data')
        os.makedirs(user_data_path, exist_ok=True)
        user_data_files = sorted(
            f for f in os.listdir(user_data_path)
            if f.endswith(('.xlsx', '.xls', '.csv')) and not f.startswith(('.', '~'))
        )

        with st.expander("🔍 Search User Data to Auto-Fill", expanded=True):
            # ── Manage user data files (upload / delete) ────────────────────
            uploaded_user_files = st.file_uploader(
                "Add user data file(s)",
                type=['xlsx', 'xls', 'csv'],
                accept_multiple_files=True,
                key=f"user_data_uploader_{st.session_state.get('user_data_uploader_key', 0)}",
                help="Upload Excel/CSV files to make them available for search & auto-fill.",
            )
            if uploaded_user_files:
                saved_any = False
                for uf in uploaded_user_files:
                    dest = os.path.join(user_data_path, os.path.basename(uf.name))
                    try:
                        with open(dest, 'wb') as out:
                            out.write(uf.getbuffer())
                        saved_any = True
                    except Exception as e:
                        st.error(f"Could not save '{uf.name}': {e}")
                if saved_any:
                    st.session_state['user_data_uploader_key'] = st.session_state.get('user_data_uploader_key', 0) + 1
                    st.success(f"Added {len(uploaded_user_files)} file(s).")
                    st.rerun()

            if not user_data_files:
                st.info("No user data files yet. Upload one above to enable search.")
            else:
                col_select, col_delete = st.columns([6, 1])
                with col_select:
                    search_file = st.selectbox(
                        "Select user data file",
                        options=user_data_files,
                        key="search_user_data_file",
                    )
                with col_delete:
                    st.markdown("<div style='height: 1.85rem'></div>", unsafe_allow_html=True)
                    if st.button("🗑️", key="delete_user_data_file", help=f"Delete '{search_file}'", use_container_width=True):
                        try:
                            os.remove(os.path.join(user_data_path, search_file))
                            st.session_state.pop('search_user_data_file', None)
                            st.success(f"Deleted '{search_file}'.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Could not delete '{search_file}': {e}")

                # Load the selected file
                search_file_path = os.path.join(user_data_path, search_file)
                try:
                    if search_file.endswith('.csv'):
                        user_df = pd.read_csv(search_file_path)
                    else:
                        user_df = pd.read_excel(search_file_path)

                    # Normalize column names to lowercase for matching
                    col_map = {c.lower().strip(): c for c in user_df.columns}
                    name_col = col_map.get('name', col_map.get('candidate_name', None))
                    email_col = col_map.get('email', col_map.get('candidate_email', None))
                    login_col = col_map.get('login_id', col_map.get('loginid', col_map.get('login', None)))
                    pass_col = col_map.get('password', col_map.get('pass', None))
                    candidate_col = col_map.get('candidate_id', col_map.get('candidateid', col_map.get('candidate id', None)))

                    if name_col and email_col:
                        search_query = st.text_input(
                            "Search by name, email" + (", or candidate ID" if candidate_col else ""),
                            key="user_search_query",
                            placeholder="Type a name, email" + (", or candidate ID" if candidate_col else "") + " to search...",
                        )

                        if search_query and len(search_query) >= 2:
                            q = search_query.lower()
                            mask = (
                                user_df[name_col].astype(str).str.lower().str.contains(q, na=False) |
                                user_df[email_col].astype(str).str.lower().str.contains(q, na=False)
                            )
                            if candidate_col:
                                mask = mask | user_df[candidate_col].astype(str).str.lower().str.contains(q, na=False)
                            results = user_df[mask].head(20)

                            if len(results) > 0:
                                st.caption(f"Found {len(results)} result(s) — click a row number to auto-fill")

                                # Build display columns
                                display_cols = [name_col, email_col]
                                if login_col:
                                    display_cols.append(login_col)
                                if pass_col:
                                    display_cols.append(pass_col)

                                for i, (_, row_data) in enumerate(results.iterrows()):
                                    r_name = str(row_data[name_col]) if pd.notna(row_data[name_col]) else ''
                                    r_email = str(row_data[email_col]) if pd.notna(row_data[email_col]) else ''
                                    r_login = str(row_data[login_col]) if login_col and pd.notna(row_data[login_col]) else ''
                                    r_pass = str(row_data[pass_col]) if pass_col and pd.notna(row_data[pass_col]) else ''
                                    r_candidate = str(row_data[candidate_col]) if candidate_col and pd.notna(row_data[candidate_col]) else ''
                                    r_candidate = r_candidate[:-2] if r_candidate.endswith('.0') else r_candidate

                                    # Clean up float-like integers (e.g. 123456.0 -> 123456)
                                    for val_name in ['r_login', 'r_pass']:
                                        val = locals()[val_name]
                                        if val.endswith('.0'):
                                            locals()[val_name] = val[:-2]
                                    r_login = r_login[:-2] if r_login.endswith('.0') else r_login
                                    r_pass = r_pass[:-2] if r_pass.endswith('.0') else r_pass

                                    btn_label = f"{r_name}  |  {r_email}"
                                    if r_candidate:
                                        btn_label += f"  |  ID: {r_candidate}"
                                    if st.button(btn_label, key=f"search_result_{i}", use_container_width=True):
                                        # Find the first empty row or add a new one
                                        rows = st.session_state.manual_entry_rows
                                        target_idx = None
                                        for ri, r in enumerate(rows):
                                            if not r.get('name', '').strip() and not r.get('email', '').strip():
                                                target_idx = ri
                                                break
                                        if target_idx is None:
                                            rows.append({'name': '', 'email': '', 'login_id': '', 'password': ''})
                                            target_idx = len(rows) - 1

                                        rows[target_idx]['name'] = r_name
                                        rows[target_idx]['email'] = r_email
                                        rows[target_idx]['login_id'] = r_login
                                        rows[target_idx]['password'] = r_pass
                                        st.rerun()
                            else:
                                st.info("No matching users found.")
                    else:
                        st.warning("User data file must have 'name' and 'email' columns.")
                except Exception as e:
                    st.error(f"Error reading user data file: {e}")

        rows = st.session_state.manual_entry_rows

        for idx in range(len(rows)):
            col_name, col_email, col_login, col_pass, col_del = st.columns([2.5, 3, 2, 2, 0.5])
            with col_name:
                rows[idx]['name'] = st.text_input(
                    "Name", value=rows[idx].get('name', ''),
                    key=f"manual_name_{idx}",
                    placeholder="e.g. Alice Smith",
                    label_visibility="collapsed" if idx > 0 else "visible"
                )
            with col_email:
                rows[idx]['email'] = st.text_input(
                    "Email", value=rows[idx].get('email', ''),
                    key=f"manual_email_{idx}",
                    placeholder="e.g. alice@example.com",
                    label_visibility="collapsed" if idx > 0 else "visible"
                )
            with col_login:
                rows[idx]['login_id'] = st.text_input(
                    "Login ID (optional)", value=rows[idx].get('login_id', ''),
                    key=f"manual_login_id_{idx}",
                    placeholder="e.g. user123",
                    label_visibility="collapsed" if idx > 0 else "visible"
                )
            with col_pass:
                rows[idx]['password'] = st.text_input(
                    "Password (optional)", value=rows[idx].get('password', ''),
                    key=f"manual_password_{idx}",
                    placeholder="e.g. pass@123",
                    label_visibility="collapsed" if idx > 0 else "visible"
                )
            with col_del:
                if idx == 0:
                    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                if len(rows) > 1:
                    if st.button("🗑️", key=f"manual_del_{idx}", help="Remove this row"):
                        rows.pop(idx)
                        st.rerun()

        # Add row button
        if st.button("➕ Add Another", key="add_manual_row"):
            rows.append({'name': '', 'email': '', 'login_id': '', 'password': ''})
            st.rerun()

        st.markdown("---")

        if st.button("✅ Load Entries", type="primary"):
            manual_students = []
            manual_errors = []
            seen_emails = set()

            for i, row in enumerate(rows, start=1):
                name = row.get('name', '').strip()
                email = row.get('email', '').strip().lower()
                login_id = row.get('login_id', '').strip()
                password = row.get('password', '').strip()

                if not name and not email:
                    continue  # skip empty rows

                if not email:
                    manual_errors.append(f"Row {i}: Email is required.")
                    continue

                if not name:
                    name = 'Unknown'

                if not FileHandler.validate_email(email):
                    manual_errors.append(f"Row {i}: Invalid email format '{email}'")
                    continue

                if email in seen_emails:
                    manual_errors.append(f"Row {i}: Duplicate email '{email}' removed")
                    continue

                seen_emails.add(email)
                student = {'name': name, 'email': email}
                if login_id:
                    student['login_id'] = login_id
                if password:
                    student['password'] = password
                manual_students.append(student)

            if manual_errors:
                with st.expander(f"⚠️ {len(manual_errors)} Warning(s)/Error(s)", expanded=True):
                    for err in manual_errors:
                        st.warning(err)

            if manual_students:
                st.session_state.students = manual_students
                st.session_state.file_errors = manual_errors
                st.success(f"✅ Successfully loaded **{len(manual_students)}** student(s)")

                preview_df = pd.DataFrame(manual_students)
                st.dataframe(preview_df, use_container_width=True, height=300)
            elif not manual_errors:
                st.error("Please enter at least one name and email.")

    # Show previously loaded data regardless of input method
    if input_method == "📁 Upload File" and st.session_state.students:
        if not (uploaded_file if 'uploaded_file' in dir() else None):
            st.info(f"📄 Previously loaded: **{len(st.session_state.students)}** student(s)")
            preview_df = pd.DataFrame(st.session_state.students)
            st.dataframe(preview_df, use_container_width=True, height=200)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: Generate Links (only when not in general email mode)
# ═══════════════════════════════════════════════════════════════════════════════
if tab3 is not None:
    with tab3:
        st.header("Step 3: Generate Login Links")

        if not st.session_state.students:
            st.warning("⚠️ Please upload student data first (Tab 2).")
        else:
            st.info(f"📊 Ready to generate links for **{len(st.session_state.students)}** student(s)")

            # Show current parameters
            st.markdown(f"""
            **API Configuration:**
            - Endpoint: `{st.session_state.api_endpoint}`
            - Program ID: `{st.session_state.program_id}`
            - Round ID: `{st.session_state.round_id}`
            - Session Time: `{st.session_state.session_time}`
            """)

            if st.button("🚀 Generate Links from API", type="primary"):
                emails = [s['email'] for s in st.session_state.students]

                api_client = APIClient(
                    api_endpoint=st.session_state.api_endpoint,
                    api_key=st.session_state.api_key,
                    timeout=Config.API_TIMEOUT
                )

                with st.spinner("Calling API to generate links..."):
                    success, response_data, error_msg = api_client.generate_links(
                        emails=emails,
                        program_id=st.session_state.program_id,
                        round_id=st.session_state.round_id,
                        session_time=st.session_state.session_time
                    )

                if success:
                    # Show raw API response for debugging
                    with st.expander("🔍 Raw API Response (Debug)"):
                        st.json(response_data)

                    # Map links and separate successful vs failed
                    students_with_links, failed_candidates = APIClient.map_links_to_students(
                        st.session_state.students,
                        response_data
                    )
                    st.session_state.students_with_links = students_with_links
                    st.session_state.failed_candidates = failed_candidates
                    st.session_state.links_generated = True

                    # ── Successful candidates (will receive emails) ──
                    if students_with_links:
                        st.success(f"✅ Successfully generated links for **{len(students_with_links)}** out of {len(st.session_state.students)} student(s)!")

                        st.subheader("📋 Candidates With Links (Will Receive Email)")
                        result_df = pd.DataFrame(students_with_links)
                        st.dataframe(result_df, use_container_width=True, height=400)

                        csv_data = result_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Successful Links CSV",
                            data=csv_data,
                            file_name=f"generated_links_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.error("❌ No links were generated for any candidate. Check the failed list below.")

                    # ── Failed candidates (will NOT receive emails) ──
                    if failed_candidates:
                        st.markdown("---")
                        st.subheader("🚫 Failed Candidates (Will NOT Receive Email)")
                        st.warning(f"{len(failed_candidates)} candidate(s) could not be found in the exam portal. No email will be sent to them.")

                        failed_df = pd.DataFrame(failed_candidates)
                        st.dataframe(failed_df, use_container_width=True, height=300)

                        failed_csv = failed_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Failed Candidates CSV",
                            data=failed_csv,
                            file_name=f"failed_candidates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            key="download_failed"
                        )
                else:
                    st.error(f"❌ Failed to generate links: {error_msg}")

            # Show previously generated links
            if st.session_state.links_generated:
                if st.session_state.students_with_links:
                    st.markdown("---")
                    st.subheader("📋 Previously Generated Links")
                    result_df = pd.DataFrame(st.session_state.students_with_links)
                    st.dataframe(result_df, use_container_width=True, height=300)

                if st.session_state.failed_candidates:
                    st.markdown("---")
                    st.subheader("🚫 Previously Failed Candidates")
                    failed_df = pd.DataFrame(st.session_state.failed_candidates)
                    st.dataframe(failed_df, use_container_width=True, height=200)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4: Email Template
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.header("Step 4: Customize Email Template")

    col_template, col_preview = st.columns([1, 1])

    with col_template:
        st.subheader("✏️ Template Editor")

        loaded_fn = st.session_state.loaded_template_filename
        loaded_name = (
            loaded_fn.replace('_', ' ').replace('.html', '').title()
            if loaded_fn else None
        )

        # ── Load a saved template ───────────────────────────────────────────
        available_templates = TemplateManager.list_templates()
        if available_templates:
            template_names = [t['name'] for t in available_templates]
            current_index = (
                template_names.index(loaded_name)
                if loaded_name in template_names else None
            )
            sel_col, del_col = st.columns([6, 1])
            with sel_col:
                selected_template = st.selectbox(
                    "📄 Load a saved template",
                    options=template_names,
                    index=current_index,
                    placeholder="Choose a template to edit...",
                    help="Pick a saved template to load it into the editor below.",
                )
            with del_col:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                delete_clicked = st.button(
                    "🗑️", key="delete_template_btn",
                    help="Delete the selected template",
                    use_container_width=True,
                    disabled=selected_template is None,
                )

            if selected_template:
                chosen = next(t for t in available_templates if t['name'] == selected_template)

                if delete_clicked:
                    TemplateManager.delete_template(chosen['filename'])
                    st.session_state.loaded_template_filename = None
                    st.toast(f"Deleted template '{selected_template}'", icon="🗑️")
                    st.rerun()

                # Load only when the user switches to a different template
                if chosen['filename'] != st.session_state.loaded_template_filename:
                    st.session_state.email_template = TemplateManager.load_template(chosen['filename'])
                    st.session_state.loaded_template_filename = chosen['filename']
                    st.session_state.template_editor_key += 1
                    if chosen.get('subject', ''):
                        st.session_state.email_subject = chosen['subject']
                    st.rerun()
        else:
            st.caption("No saved templates yet — build one below and save it.")

        # Status line: what is currently in the editor
        if loaded_name:
            st.caption(f"📝 Editing saved template: **{loaded_name}**")
        else:
            st.caption("📝 Editing an unsaved draft")

        st.divider()

        # ── Editor fields ───────────────────────────────────────────────────
        custom_program_name = st.text_input(
            "Program Name (override)",
            value=st.session_state.custom_program_name,
            help="Replaces {program_name} in the subject & template. Leave empty to use the name from the API.",
            placeholder="e.g. Software Engineering Assessment"
        )
        st.session_state.custom_program_name = custom_program_name

        email_subject = st.text_input(
            "Email Subject",
            value=st.session_state.email_subject,
            help="You can use placeholders like {program_name}, {name}"
        )
        st.session_state.email_subject = email_subject

        # Template editor (key changes when visual editor applies edits)
        email_template = st.text_area(
            "HTML Email Template",
            value=st.session_state.email_template,
            height=500,
            help="Edit the HTML template. Use placeholders for dynamic content.",
            key=f"email_template_editor_{st.session_state.template_editor_key}",
        )
        st.session_state.email_template = email_template

        # ── Action row: Save / Save as new / Reset ──────────────────────────
        if loaded_name:
            c_save, c_saveas, c_reset = st.columns(3)
            with c_save:
                if st.button("💾 Save", key="save_overwrite_tpl",
                             use_container_width=True,
                             help=f"Overwrite '{loaded_name}' with the current subject & HTML."):
                    TemplateManager.update_template(loaded_fn, email_subject, email_template)
                    st.toast(f"Saved '{loaded_name}'", icon="✅")
                    st.rerun()
        else:
            c_saveas, c_reset = st.columns(2)

        with c_saveas:
            if st.button("📑 Save as new", key="save_as_toggle", use_container_width=True):
                st.session_state.show_save_as = not st.session_state.get('show_save_as', False)
        with c_reset:
            if st.button("🔄 Reset", key="reset_tpl", use_container_width=True,
                         help="Reset the editor to the built-in default template."):
                if st.session_state.skip_link_generation:
                    st.session_state.email_template = TemplateManager.get_general_email_template()
                    st.session_state.email_subject = 'Invitation to Online Assessment | TAM – Digital Banking | 26 February'
                else:
                    st.session_state.email_template = TemplateManager.get_default_template()
                    st.session_state.email_subject = 'Assessment Link & Login Credentials | TAM – Digital Banking | 26 February'
                st.session_state.loaded_template_filename = None
                st.session_state.template_editor_key += 1
                st.rerun()

        # Inline "Save as new" form (revealed by the button above)
        if st.session_state.get('show_save_as', False):
            with st.container(border=True):
                st.markdown("**Save as a new template**")
                save_as_name = st.text_input(
                    "New template name",
                    key="save_as_name",
                    placeholder="e.g. Marketing Campaign Q1",
                )
                c_confirm, c_cancel = st.columns(2)
                with c_confirm:
                    if st.button("💾 Save", key="save_as_confirm", use_container_width=True):
                        if not save_as_name.strip():
                            st.error("Please enter a name for the new template.")
                        else:
                            new_fn = TemplateManager.save_template(
                                save_as_name, email_subject, email_template
                            )
                            st.session_state.loaded_template_filename = new_fn
                            st.session_state.show_save_as = False
                            st.toast(f"Saved new template '{save_as_name.strip()}'", icon="✅")
                            st.rerun()
                with c_cancel:
                    if st.button("Cancel", key="save_as_cancel", use_container_width=True):
                        st.session_state.show_save_as = False
                        st.rerun()

    with col_preview:
        st.subheader("👁️ Preview")

        # Toggle between static preview and visual editor
        visual_mode = st.toggle(
            "✏️ Visual Editor",
            value=st.session_state.visual_editor_active,
            help="Edit text directly in the preview with a floating toolbar",
        )
        st.session_state.visual_editor_active = visual_mode

        # Detect if students have login_id / password
        _students_data = st.session_state.get('students', [])
        _has_login_id = any(s.get('login_id') for s in _students_data)
        _has_password = any(s.get('password') for s in _students_data)

        # Available placeholders
        with st.expander("📌 Available Placeholders"):
            placeholders = TemplateManager.get_available_placeholders(
                general_mode=st.session_state.get('skip_link_generation', False),
                has_login_id=_has_login_id,
                has_password=_has_password,
            )
            placeholder_df = pd.DataFrame(placeholders)
            st.table(placeholder_df)

        if visual_mode:
            # ── Visual WYSIWYG Editor ─────────────────────────────────
            st.markdown("**Visual Editor** — click text to edit, then press 💾 **Apply Changes**")
            edited = visual_editor(
                template_html=st.session_state.email_template,
                key="visual_editor_component",
            )
            if edited is not None and edited != st.session_state.email_template:
                st.session_state.email_template = edited
                st.session_state.template_editor_key += 1   # force code editor refresh
                st.rerun()
        else:
            # ── Static Preview ────────────────────────────────────────
            st.markdown("**Email Preview (with sample data):**")
            sample_data = TemplateManager.get_sample_data(
                general_mode=st.session_state.get('skip_link_generation', False),
                has_login_id=_has_login_id,
                has_password=_has_password,
            )
            if st.session_state.custom_program_name:
                sample_data['program_name'] = st.session_state.custom_program_name

            # Replace placeholders in subject
            preview_subject = email_subject
            for key, value in sample_data.items():
                preview_subject = preview_subject.replace(f'{{{key}}}', str(value))

            st.markdown(f"**Subject:** {preview_subject}")

            # Replace placeholders in template
            preview_html = email_template
            for key, value in sample_data.items():
                preview_html = preview_html.replace(f'{{{key}}}', str(value))

            st.components.v1.html(preview_html, height=600, scrolling=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5: Send Emails
# ═══════════════════════════════════════════════════════════════════════════════
with tab5:
    if st.session_state.skip_link_generation:
        st.header("Send Emails")
    else:
        st.header("Step 5: Send Emails")

    # Determine if we're ready to send
    if st.session_state.skip_link_generation:
        # General email mode — use uploaded students directly
        _ready_to_send = len(st.session_state.students) > 0
        if not _ready_to_send:
            st.warning("⚠️ Please upload student data first (Tab 2).")
    else:
        _ready_to_send = st.session_state.links_generated
        if not _ready_to_send:
            st.warning("⚠️ Please generate links first (Tab 3).")

    if _ready_to_send:
        # Build list of students to email
        if st.session_state.skip_link_generation:
            # Prepare students without links — just name & email (+ optional login_id/password)
            students_to_email = [
                {
                    'name': s['name'],
                    'email': s['email'],
                    'candidate_id': '',
                    'login_link': '',
                    'expires_at': '',
                    'program_name': st.session_state.custom_program_name or '',
                    'round_name': '',
                    'login_id': s.get('login_id', ''),
                    'password': s.get('password', ''),
                    'email_status': 'pending',
                }
                for s in st.session_state.students
            ]
        else:
            students_to_email = [s for s in st.session_state.students_with_links if s.get('login_link') not in (None, 'N/A', '')]

        if not students_to_email:
            if st.session_state.skip_link_generation:
                st.warning("⚠️ No students found. Please upload student data in Tab 2.")
            else:
                st.warning("⚠️ No candidates with valid links to send emails to. Check the failed candidates list in Tab 3.")

        if not st.session_state.skip_link_generation and st.session_state.failed_candidates:
            st.info(f"ℹ️ {len(st.session_state.failed_candidates)} candidate(s) were skipped (not found in exam portal). Only candidates with valid links will receive emails.")

        # Pre-send checklist
        st.subheader("📋 Pre-Send Checklist")

        check_col1, check_col2 = st.columns(2)
        with check_col1:
            st.markdown(f"✅ **Students to email:** {len(students_to_email)}")
            if st.session_state.skip_link_generation:
                st.markdown("✅ **Mode:** General Email (no login links)")
            else:
                st.markdown(f"✅ **Links generated:** {st.session_state.links_generated}")
            st.markdown(f"✅ **Email template ready:** {'Yes' if st.session_state.email_template else 'No'}")

        with check_col2:
            st.markdown(f"📧 **Sender:** {st.session_state.sender_name} <{st.session_state.sender_email}>")
            st.markdown(f"☁️ **Service:** AWS SES ({st.session_state.aws_region})")
            st.markdown(f"📝 **Subject:** {st.session_state.email_subject}")
            st.markdown(f"⏱️ **Delay between emails:** {Config.DELAY_BETWEEN_EMAILS}s")

        st.markdown("---")

        # ── Resume from Crash Section ──────────────────────────────────────────
        resumable_session = EmailSender.get_resumable_session()
        if resumable_session:
            st.markdown("---")
            st.subheader("🔄 Resume Previous Session")
            st.warning(
                f"⚠️ **A previous email session was interrupted!**\n\n"
                f"- **Status:** {resumable_session['status'].upper()}\n"
                f"- **Processed:** {resumable_session['processed']}/{resumable_session['total']} emails\n"
                f"- **Sent:** {resumable_session['sent']} ✅ | **Failed:** {resumable_session['failed']} ❌\n"
                f"- **Remaining:** {resumable_session['remaining']} emails\n"
                f"- **Started at:** {resumable_session['started_at']}"
                + (f"\n- **Error:** {resumable_session['crash_error']}" if resumable_session.get('crash_error') else "")
            )

            resume_col1, resume_col2 = st.columns(2)
            with resume_col1:
                if st.button("🔄 Resume Sending", type="primary"):
                    if not st.session_state.aws_access_key or not st.session_state.aws_secret_key:
                        st.error("❌ Please configure AWS SES credentials first.")
                    else:
                        ses_config = {
                            'aws_access_key': st.session_state.aws_access_key,
                            'aws_secret_key': st.session_state.aws_secret_key,
                            'aws_region': st.session_state.aws_region,
                            'sender_email': st.session_state.sender_email,
                            'sender_name': st.session_state.sender_name,
                            'configuration_set': Config.AWS_SES_CONFIGURATION_SET,
                        }
                        resume_sender = EmailSender(ses_config)

                        with st.spinner("Testing AWS SES connection..."):
                            conn_ok, conn_msg = resume_sender.test_connection()

                        if not conn_ok:
                            st.error(f"❌ AWS SES connection failed: {conn_msg}")
                        else:
                            st.success(f"✅ Connected! Resuming from email {resumable_session['processed'] + 1}...")

                            resume_progress = st.progress(resumable_session['processed'] / resumable_session['total'])
                            resume_status = st.empty()
                            resume_counts = {'sent': resumable_session['sent'], 'failed': resumable_session['failed']}

                            def resume_progress_callback(current, total, email, success, message):
                                if not email.startswith("(resumed"):
                                    if success:
                                        resume_counts['sent'] += 1
                                    else:
                                        resume_counts['failed'] += 1
                                progress = current / total
                                resume_progress.progress(progress)
                                status_icon = "✅" if success else "❌"
                                resume_status.markdown(
                                    f"**Progress:** {current}/{total} | "
                                    f"✅ Sent: {resume_counts['sent']} | ❌ Failed: {resume_counts['failed']} | "
                                    f"Last: {status_icon} {email}"
                                )

                            cal_config = None
                            if st.session_state.include_calendar_event:
                                cal_config = {
                                    'event_type': st.session_state.calendar_event_type,
                                    'title': st.session_state.calendar_event_title,
                                    'date_str': st.session_state.calendar_event_date.strftime('%Y-%m-%d') if st.session_state.calendar_event_date else '',
                                    'start_time_str': st.session_state.calendar_event_start_time.strftime('%H:%M'),
                                    'duration_str': st.session_state.calendar_event_duration or '1 hour',
                                    'organizer_name': st.session_state.calendar_event_organizer_name or st.session_state.sender_name,
                                    'organizer_email': st.session_state.calendar_event_organizer_email or st.session_state.sender_email,
                                    'location': st.session_state.calendar_event_location,
                                    'meeting_link': st.session_state.calendar_event_meeting_link,
                                    'description': st.session_state.calendar_event_description,
                                }

                            try:
                                results = resume_sender.send_bulk_emails(
                                    students=students_to_email,
                                    subject=st.session_state.email_subject,
                                    html_template=st.session_state.email_template,
                                    delay=float(Config.DELAY_BETWEEN_EMAILS),
                                    progress_callback=resume_progress_callback,
                                    calendar_event_config=cal_config,
                                    checkpoint_interval=10,
                                    resume_from_checkpoint=True,
                                )
                                st.session_state.email_results = results
                                st.session_state.emails_sent = True
                                st.success(f"✅ Resume complete! Sent: {resume_counts['sent']} | Failed: {resume_counts['failed']}")
                                st.balloons()
                            except Exception as e:
                                st.error(f"⚠️ Crashed again: {str(e)}. Progress saved — you can resume again.")

            with resume_col2:
                if st.button("🗑️ Discard & Start Fresh"):
                    EmailSender.clear_checkpoint(resumable_session.get('checkpoint_file'))
                    st.success("✅ Previous session cleared. You can start a fresh send.")
                    st.rerun()

            st.markdown("---")

        # Email sending settings
        st.subheader("⚙️ Sending Settings")
        delay_between = st.slider(
            "Delay between emails (seconds)",
            min_value=0.01,
            max_value=10.0,
            value=float(Config.DELAY_BETWEEN_EMAILS),
            step=0.01,
            help="Time to wait between sending each email (to avoid rate limits)"
        )

        # Preview recipients
        with st.expander(f"👥 Preview Recipients ({len(students_to_email)})"):
            if st.session_state.skip_link_generation:
                preview_df = pd.DataFrame(students_to_email)[['name', 'email']]
            else:
                preview_df = pd.DataFrame(students_to_email)[['name', 'email', 'candidate_id', 'login_link']]
            st.dataframe(preview_df, use_container_width=True)

        st.markdown("---")

        # ── Calendar Event Options ─────────────────────────────────────────────
        st.subheader("📅 Calendar Event (Optional)")
        st.markdown(
            "Attach a calendar invite to each email so recipients can add the exam session "
            "to their calendar. Supported formats: **Google Meet** and **Outlook / Microsoft Teams**."
        )

        include_event = st.checkbox(
            "Include calendar event (attach .ics invite to each email)",
            value=st.session_state.include_calendar_event,
        )
        st.session_state.include_calendar_event = include_event

        if include_event:
            st.markdown("**Select event type:**")
            event_type_choice = st.radio(
                "Calendar Platform",
                options=[CalendarEvent.EVENT_TYPE_GOOGLE, CalendarEvent.EVENT_TYPE_OUTLOOK],
                format_func=CalendarEvent.get_event_type_label,
                index=0 if st.session_state.calendar_event_type == CalendarEvent.EVENT_TYPE_GOOGLE else 1,
                horizontal=True,
                label_visibility="collapsed",
            )
            st.session_state.calendar_event_type = event_type_choice

            st.markdown("**Event Details** *(fill in as plain text)*")

            ev_col1, ev_col2 = st.columns(2)

            with ev_col1:
                ev_title = st.text_input(
                    "Event Title *",
                    value=st.session_state.calendar_event_title,
                    placeholder="e.g. Software Engineering Exam",
                    help="Title of the calendar event",
                )
                st.session_state.calendar_event_title = ev_title

                ev_date = st.date_input(
                    "Event Date *",
                    value=st.session_state.calendar_event_date,
                    format="YYYY-MM-DD",
                    help="Select the date of the exam session",
                )
                st.session_state.calendar_event_date = ev_date

                ev_start_time = st.time_input(
                    "Start Time *",
                    value=st.session_state.calendar_event_start_time,
                    step=300,
                    help="Select the start time (5-minute increments)",
                )
                st.session_state.calendar_event_start_time = ev_start_time

                st.markdown(r"**Duration \*:**")
                dur_col_h, dur_col_m = st.columns(2)
                with dur_col_h:
                    ev_dur_hours = st.number_input(
                        "Hours",
                        min_value=0,
                        max_value=23,
                        value=st.session_state.calendar_event_duration_hours,
                        step=1,
                    )
                    st.session_state.calendar_event_duration_hours = ev_dur_hours
                with dur_col_m:
                    ev_dur_mins = st.number_input(
                        "Minutes",
                        min_value=0,
                        max_value=55,
                        value=st.session_state.calendar_event_duration_minutes,
                        step=5,
                    )
                    st.session_state.calendar_event_duration_minutes = ev_dur_mins

                # Compose duration string for the ICS generator
                if ev_dur_hours > 0 and ev_dur_mins > 0:
                    ev_duration = f"{ev_dur_hours}h {ev_dur_mins}m"
                elif ev_dur_hours > 0:
                    ev_duration = f"{ev_dur_hours}h"
                elif ev_dur_mins > 0:
                    ev_duration = f"{ev_dur_mins}m"
                else:
                    ev_duration = "1h"  # fallback
                st.session_state.calendar_event_duration = ev_duration

            with ev_col2:
                ev_organizer_name = st.text_input(
                    "Organizer Name",
                    value=st.session_state.calendar_event_organizer_name or st.session_state.sender_name,
                    placeholder="e.g. Exam Portal Team",
                    help="Name of the event organizer (defaults to sender name)",
                )
                st.session_state.calendar_event_organizer_name = ev_organizer_name

                ev_organizer_email = st.text_input(
                    "Organizer Email",
                    value=st.session_state.calendar_event_organizer_email or st.session_state.sender_email,
                    placeholder="e.g. exams@yourcompany.com",
                    help="Organizer's email address (defaults to sender email)",
                )
                st.session_state.calendar_event_organizer_email = ev_organizer_email

                ev_meeting_link = st.text_input(
                    "Meeting Link",
                    value=st.session_state.calendar_event_meeting_link,
                    placeholder=(
                        "e.g. https://meet.google.com/abc-xyz"
                        if event_type_choice == CalendarEvent.EVENT_TYPE_GOOGLE
                        else "e.g. https://teams.microsoft.com/..."
                    ),
                    help="Video conference URL (Google Meet or Teams link)",
                )
                st.session_state.calendar_event_meeting_link = ev_meeting_link

                ev_location = st.text_input(
                    "Physical Location (optional)",
                    value=st.session_state.calendar_event_location,
                    placeholder="e.g. Room 101, Main Building",
                    help="Physical location or leave blank if online only",
                )
                st.session_state.calendar_event_location = ev_location

            ev_description = st.text_area(
                "Event Description (optional)",
                value=st.session_state.calendar_event_description,
                placeholder="e.g. Please join this session for your exam. Make sure you have a stable internet connection.",
                height=80,
                help="Additional instructions or notes for attendees",
            )
            st.session_state.calendar_event_description = ev_description

            # Validate required fields and show preview
            missing_event_fields = []
            if not ev_title.strip():
                missing_event_fields.append("Event Title")
            if ev_date is None:
                missing_event_fields.append("Event Date")

            if missing_event_fields:
                st.warning(f"⚠️ Calendar event is missing: {', '.join(missing_event_fields)}")
            else:
                from modules.calendar_event import CalendarEvent as _CE
                _sample_ics, _sample_err = _CE.generate_ics(
                    event_type=event_type_choice,
                    title=ev_title,
                    date_str=ev_date.strftime('%Y-%m-%d'),
                    start_time_str=ev_start_time.strftime('%H:%M'),
                    duration_str=ev_duration or '1 hour',
                    organizer_name=ev_organizer_name or st.session_state.sender_name,
                    organizer_email=ev_organizer_email or st.session_state.sender_email,
                    attendee_name='Sample Attendee',
                    attendee_email='sample@example.com',
                    location=ev_location,
                    meeting_link=ev_meeting_link,
                    description=ev_description,
                )
                if _sample_err:
                    st.error(f"❌ Calendar event error: {_sample_err}")
                else:
                    platform_label = CalendarEvent.get_event_type_label(event_type_choice)
                    st.success(
                        f"✅ Calendar invite ready — **{platform_label}** event "
                        f"**'{ev_title}'** on **{ev_date.strftime('%d %b %Y')}** at **{ev_start_time.strftime('%H:%M')}** "
                        f"for **{ev_duration}**. Each recipient will receive a personalised .ics attachment."
                    )

        st.markdown("---")

        # Confirmation
        confirm = st.checkbox(
            f"I confirm sending emails to **{len(students_to_email)}** recipient(s)",
            value=False
        )

        # Final-review confirmation modal — last check before sending
        @st.dialog("📋 Final Review — Confirm Before Sending", width="large")
        def _confirm_send_dialog():
            review_recipient = students_to_email[0] if students_to_email else {}
            review_subject = EmailSender._replace_placeholders(
                st.session_state.email_subject, review_recipient
            )
            review_html = EmailSender._replace_placeholders(
                st.session_state.email_template, review_recipient
            )
            st.markdown(
                f"You're about to send **{len(students_to_email)}** email(s). "
                "Review the exact subject and content below before sending."
            )
            st.markdown(f"**Subject:** {review_subject}")
            if review_recipient.get('email'):
                st.caption(
                    "Preview rendered for the first recipient: "
                    f"{review_recipient.get('name', '')} <{review_recipient.get('email', '')}>"
                )
            st.components.v1.html(review_html, height=400, scrolling=True)
            st.markdown("---")
            dlg_col1, dlg_col2 = st.columns(2)
            with dlg_col1:
                if st.button("✅ Confirm & Send", type="primary", use_container_width=True):
                    st.session_state.do_send_emails = True
                    st.rerun()
            with dlg_col2:
                if st.button("Cancel", use_container_width=True):
                    st.rerun()

        # Open the dialog only on the button press. Streamlit keeps it open across
        # internal reruns and closes it on the ✕ — so we must NOT re-open it from a
        # sticky session flag (that overlay would reappear on every rerun, even on
        # other tabs, e.g. after clicking Save in the Template tab).
        if st.button("📨 Send All Emails", type="primary", disabled=not confirm):
            _confirm_send_dialog()

        # The dialog's "Confirm & Send" sets do_send_emails and calls st.rerun(),
        # which closes the modal. We land here on that next run with the dialog
        # gone. Pause ~1s (inside a spinner so the closed state is painted) before
        # kicking off the blocking send loop, so the modal is visibly dismissed
        # first. (Don't chain extra st.rerun() calls — Streamlit batches chained
        # reruns into a single frontend repaint, which would leave the overlay up
        # until sending finished.)
        if st.session_state.get('do_send_emails'):
            st.session_state.do_send_emails = False
            with st.spinner("Starting…"):
                time.sleep(1)
            if not st.session_state.aws_access_key or not st.session_state.aws_secret_key:
                st.error("❌ Please configure AWS SES credentials in Tab 1.")
            else:
                ses_config = {
                    'aws_access_key': st.session_state.aws_access_key,
                    'aws_secret_key': st.session_state.aws_secret_key,
                    'aws_region': st.session_state.aws_region,
                    'sender_email': st.session_state.sender_email,
                    'sender_name': st.session_state.sender_name,
                    'configuration_set': Config.AWS_SES_CONFIGURATION_SET,
                }

                email_sender = EmailSender(ses_config)

                # Test connection first
                with st.spinner("Testing AWS SES connection..."):
                    conn_success, conn_msg = email_sender.test_connection()

                if not conn_success:
                    st.error(f"❌ AWS SES connection failed: {conn_msg}")
                else:
                    st.success("✅ AWS SES connection verified!")

                    # Progress tracking
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    results_container = st.container()

                    counts = {'sent': 0, 'failed': 0}

                    def progress_callback(current, total, email, success, message):
                        if success:
                            counts['sent'] += 1
                        else:
                            counts['failed'] += 1

                        progress = current / total
                        progress_bar.progress(progress)
                        status_icon = "✅" if success else "❌"
                        status_text.markdown(
                            f"**Progress:** {current}/{total} | "
                            f"✅ Sent: {counts['sent']} | ❌ Failed: {counts['failed']} | "
                            f"Last: {status_icon} {email}"
                        )

                        # Save intermediate results to session state every 10 emails
                        # so partial data survives Streamlit reruns
                        if current % 10 == 0:
                            st.session_state.email_results_partial = True

                    # Override program_name if custom value is set
                    if st.session_state.custom_program_name:
                        for s in students_to_email:
                            s['program_name'] = st.session_state.custom_program_name

                    # Build calendar event config if enabled
                    cal_config = None
                    if st.session_state.include_calendar_event:
                        cal_config = {
                            'event_type': st.session_state.calendar_event_type,
                            'title': st.session_state.calendar_event_title,
                            'date_str': st.session_state.calendar_event_date.strftime('%Y-%m-%d') if st.session_state.calendar_event_date else '',
                            'start_time_str': st.session_state.calendar_event_start_time.strftime('%H:%M'),
                            'duration_str': st.session_state.calendar_event_duration or '1 hour',
                            'organizer_name': st.session_state.calendar_event_organizer_name or st.session_state.sender_name,
                            'organizer_email': st.session_state.calendar_event_organizer_email or st.session_state.sender_email,
                            'location': st.session_state.calendar_event_location,
                            'meeting_link': st.session_state.calendar_event_meeting_link,
                            'description': st.session_state.calendar_event_description,
                        }

                    # Send emails with crash protection
                    results = None
                    try:
                        results = email_sender.send_bulk_emails(
                            students=students_to_email,
                            subject=st.session_state.email_subject,
                            html_template=st.session_state.email_template,
                            delay=delay_between,
                            progress_callback=progress_callback,
                            calendar_event_config=cal_config,
                            checkpoint_interval=10,
                        )
                    except Exception as e:
                        st.error(
                            f"⚠️ **Email sending crashed after {counts['sent'] + counts['failed']} emails!**\n\n"
                            f"**Error:** {str(e)}\n\n"
                            f"✅ Sent: {counts['sent']} | ❌ Failed: {counts['failed']} | "
                            f"📭 Not sent: {len(students_to_email) - counts['sent'] - counts['failed']}\n\n"
                            f"📁 A crash report has been auto-saved to the `reports/` folder.\n\n"
                            f"🔄 **You can resume sending** from where it stopped — reload the app and use the Resume button."
                        )
                        # Load partial results from the checkpoint
                        resumable = EmailSender.get_resumable_session()
                        if resumable:
                            checkpoint_data = EmailSender._load_latest_checkpoint()
                            if checkpoint_data:
                                results = checkpoint_data.get('results', [])

                    if results:
                        st.session_state.email_results = results
                        st.session_state.emails_sent = True

                    # Final summary
                    st.markdown("---")
                    st.subheader("📊 Sending Complete!")

                    summary_col1, summary_col2, summary_col3 = st.columns(3)
                    with summary_col1:
                        st.metric("Total Emails", counts['sent'] + counts['failed'])
                    with summary_col2:
                        st.metric("Successfully Sent", counts['sent'])
                    with summary_col3:
                        st.metric("Failed", counts['failed'])

                    if counts['failed'] > 0:
                        st.warning("Some emails failed to send. Check the Reports tab for details.")

                    if results and len(results) == len(students_to_email):
                        st.balloons()

        # Show previous results if available
        if st.session_state.emails_sent and st.session_state.email_results:
            st.markdown("---")
            st.subheader("📋 Previous Send Results")
            results_df = pd.DataFrame(st.session_state.email_results)
            st.dataframe(
                results_df[['name', 'email', 'email_status', 'email_message', 'send_time']],
                use_container_width=True
            )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 6: Reports
# ═══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.header("Step 6: Reports & Downloads")

    if not st.session_state.email_results and not st.session_state.students_with_links:
        st.info("📊 Reports will appear here after generating links or sending emails.")
    else:
        # --- Links Report ---
        if st.session_state.students_with_links:
            st.subheader("🔗 Generated Links Report")

            links_df = pd.DataFrame(st.session_state.students_with_links)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Students", len(links_df))
            with col2:
                has_link = len(links_df[links_df['login_link'] != 'N/A'])
                st.metric("Links Generated", has_link)
            with col3:
                no_link = len(links_df[links_df['login_link'] == 'N/A'])
                st.metric("Missing Links", no_link)

            st.dataframe(links_df, use_container_width=True, height=300)

            csv_links = links_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Links Report (CSV)",
                data=csv_links,
                file_name=f"links_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key="download_links"
            )

        # --- Email Results Report ---
        if st.session_state.email_results:
            st.markdown("---")
            st.subheader("📧 Email Sending Report")

            results_df = pd.DataFrame(st.session_state.email_results)

            # Summary metrics
            total = len(results_df)
            sent = len(results_df[results_df['email_status'] == 'sent'])
            failed = len(results_df[results_df['email_status'] == 'failed'])
            pending = len(results_df[results_df['email_status'] == 'pending'])

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total", total)
            with col2:
                st.metric("Sent ✅", sent)
            with col3:
                st.metric("Failed ❌", failed)
            with col4:
                success_rate = (sent / total * 100) if total > 0 else 0
                st.metric("Success Rate", f"{success_rate:.1f}%")

            # Status chart
            if total > 0:
                status_counts = results_df['email_status'].value_counts()
                st.bar_chart(status_counts)

            # Detailed results
            st.subheader("📋 Detailed Results")
            display_cols = ['name', 'email', 'candidate_id', 'email_status', 'email_message', 'send_time']
            available_cols = [c for c in display_cols if c in results_df.columns]
            st.dataframe(results_df[available_cols], use_container_width=True, height=400)

            # Filter by status
            status_filter = st.selectbox(
                "Filter by status",
                options=['All', 'sent', 'failed', 'pending']
            )
            if status_filter != 'All':
                filtered_df = results_df[results_df['email_status'] == status_filter]
                st.dataframe(filtered_df[available_cols], use_container_width=True)

            # Download
            csv_results = results_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Email Report (CSV)",
                data=csv_results,
                file_name=f"email_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key="download_email_report"
            )

            # Failed emails for retry
            if failed > 0:
                st.markdown("---")
                st.subheader("🔄 Failed Emails")
                failed_df = results_df[results_df['email_status'] == 'failed']
                st.dataframe(
                    failed_df[['name', 'email', 'email_message']],
                    use_container_width=True
                )

                failed_csv = failed_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Failed Emails (CSV)",
                    data=failed_csv,
                    file_name=f"failed_emails_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key="download_failed"
                )

    # --- Saved Reports on Disk (crash reports, auto-saved reports) ---
    st.markdown("---")
    st.subheader("💾 Saved Reports on Disk")
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
    if os.path.exists(reports_dir):
        report_files = sorted(
            [f for f in os.listdir(reports_dir) if f.endswith('.csv') or f.endswith('.txt')],
            reverse=True
        )
        crash_reports = [f for f in report_files if f.lower().startswith('crash')]
        normal_reports = [f for f in report_files if not f.lower().startswith('crash') and not f.startswith('checkpoint_')]

        # Keep only the latest 3 auto-saved reports; delete older ones from disk.
        normal_reports.sort(key=lambda f: os.path.getmtime(os.path.join(reports_dir, f)), reverse=True)
        for stale in normal_reports[3:]:
            try:
                os.remove(os.path.join(reports_dir, stale))
            except Exception:
                pass
        normal_reports = normal_reports[:3]

        all_reports = crash_reports + normal_reports

        if all_reports:
            # Delete All button
            del_all_col1, del_all_col2 = st.columns([3, 1])
            with del_all_col2:
                if st.button("🗑️ Delete All Reports", type="secondary", key="delete_all_reports"):
                    for fname in all_reports:
                        try:
                            os.remove(os.path.join(reports_dir, fname))
                        except Exception:
                            pass
                    # Also clean up checkpoint files
                    for fname in os.listdir(reports_dir):
                        if fname.startswith('checkpoint_') and fname.endswith('.json'):
                            try:
                                os.remove(os.path.join(reports_dir, fname))
                            except Exception:
                                pass
                    st.success("✅ All reports deleted.")
                    st.rerun()

        if crash_reports:
            st.warning(f"⚠️ **{len(crash_reports)} crash report(s) found:**")
            for fname in crash_reports:
                fpath = os.path.join(reports_dir, fname)
                with open(fpath, 'r', encoding='utf-8') as rf:
                    file_data = rf.read()
                col_a, col_b, col_c = st.columns([3, 1, 1])
                with col_a:
                    st.text(f"📄 {fname}")
                with col_b:
                    st.download_button(
                        label="📥 Download",
                        data=file_data,
                        file_name=fname,
                        mime="text/csv" if fname.endswith('.csv') else "text/plain",
                        key=f"download_report_{fname}"
                    )
                with col_c:
                    if st.button("🗑️ Delete", key=f"delete_report_{fname}"):
                        try:
                            os.remove(fpath)
                            st.success(f"Deleted {fname}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to delete: {e}")

        if normal_reports:
            st.info(f"📁 **{len(normal_reports)} auto-saved report(s):**")
            for fname in normal_reports:
                fpath = os.path.join(reports_dir, fname)
                with open(fpath, 'r', encoding='utf-8') as rf:
                    file_data = rf.read()
                col_a, col_b, col_c = st.columns([3, 1, 1])
                with col_a:
                    st.text(f"📄 {fname}")
                with col_b:
                    st.download_button(
                        label="📥 Download",
                        data=file_data,
                        file_name=fname,
                        mime="text/csv",
                        key=f"download_report_{fname}"
                    )
                with col_c:
                    if st.button("🗑️ Delete", key=f"delete_report_{fname}"):
                        try:
                            os.remove(fpath)
                            st.success(f"Deleted {fname}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to delete: {e}")

        if not crash_reports and not normal_reports:
            st.info("No saved reports found on disk yet.")
    else:
        st.info("No saved reports found on disk yet.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 7: Email Tracking (CloudWatch Metrics)
# ═══════════════════════════════════════════════════════════════════════════════
with tab7:
    st.header("Email Tracking Dashboard")

    if not Config.AWS_SES_CONFIGURATION_SET:
        st.warning(
            "No SES Configuration Set configured. "
            "Set `AWS_SES_CONFIGURATION_SET` in your `.env` file to enable tracking."
        )
    else:
        st.markdown(f"**Configuration Set:** `{Config.AWS_SES_CONFIGURATION_SET}`")

        # Time range selector
        time_range = st.selectbox(
            "Time range",
            options=[
                ("Last 1 hour", 1),
                ("Last 6 hours", 6),
                ("Last 24 hours", 24),
                ("Last 3 days", 72),
                ("Last 7 days", 168),
                ("Last 14 days", 336),
                ("Last 30 days", 720),
            ],
            format_func=lambda x: x[0],
            index=2,
        )
        hours = time_range[1]

        # Choose aggregation period based on time range
        if hours <= 6:
            period = 300  # 5 min
        elif hours <= 72:
            period = 3600  # 1 hour
        else:
            period = 86400  # 1 day

        if st.button("Refresh Metrics", type="primary"):
            st.session_state.pop('_tracking_cache', None)

        # Fetch metrics
        try:
            tracker = EmailTracker(
                aws_access_key=st.session_state.aws_access_key,
                aws_secret_key=st.session_state.aws_secret_key,
                aws_region=st.session_state.aws_region,
                configuration_set=Config.AWS_SES_CONFIGURATION_SET,
            )

            with st.spinner("Fetching metrics from CloudWatch..."):
                metrics = tracker.get_all_metrics(hours=hours, period=period)

            if metrics.get('error'):
                st.error(f"Error fetching metrics: {metrics['error']}")
            else:
                totals = metrics['totals']
                rates = EmailTracker.get_rates(totals)

                # ── Summary Metrics ──
                st.subheader("Summary")
                m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
                m1.metric("Sent", f"{int(totals.get('Send', 0))}")
                m2.metric("Delivered", f"{int(totals.get('Delivery', 0))}")
                m3.metric("Opens", f"{int(totals.get('Open', 0))}")
                m4.metric("Clicks", f"{int(totals.get('Click', 0))}")
                m5.metric("Bounces", f"{int(totals.get('Bounce', 0))}")
                m6.metric("Complaints", f"{int(totals.get('Complaint', 0))}")
                m7.metric("Rejects", f"{int(totals.get('Reject', 0))}")

                # ── Rates ──
                st.subheader("Rates")
                r1, r2, r3, r4, r5 = st.columns(5)
                r1.metric("Delivery Rate", f"{rates['delivery_rate']:.1f}%")
                r2.metric("Open Rate", f"{rates['open_rate']:.1f}%")
                r3.metric("Click Rate", f"{rates['click_rate']:.1f}%")
                r4.metric("Bounce Rate", f"{rates['bounce_rate']:.1f}%")
                r5.metric("Complaint Rate", f"{rates['complaint_rate']:.1f}%")

                # ── Time-Series Charts ──
                st.subheader("Trends")
                timeseries = metrics['timeseries']

                # Build a combined dataframe for charting
                import pandas as _pd

                chart_records = []
                for metric_name, datapoints in timeseries.items():
                    for dp in datapoints:
                        chart_records.append({
                            'Time': dp['timestamp'],
                            'Metric': metric_name,
                            'Count': dp['value'],
                        })

                if chart_records:
                    chart_df = _pd.DataFrame(chart_records)

                    # Delivery & Send chart
                    delivery_df = chart_df[chart_df['Metric'].isin(['Send', 'Delivery'])]
                    if not delivery_df.empty:
                        st.markdown("**Send vs Delivery**")
                        pivot = delivery_df.pivot_table(
                            index='Time', columns='Metric', values='Count', aggfunc='sum'
                        ).fillna(0)
                        st.line_chart(pivot)

                    # Engagement chart (Open + Click)
                    engage_df = chart_df[chart_df['Metric'].isin(['Open', 'Click'])]
                    if not engage_df.empty:
                        st.markdown("**Opens & Clicks**")
                        pivot = engage_df.pivot_table(
                            index='Time', columns='Metric', values='Count', aggfunc='sum'
                        ).fillna(0)
                        st.line_chart(pivot)

                    # Bounce & Complaint chart
                    issue_df = chart_df[chart_df['Metric'].isin(['Bounce', 'Complaint', 'Reject'])]
                    if not issue_df.empty:
                        st.markdown("**Bounces, Complaints & Rejects**")
                        pivot = issue_df.pivot_table(
                            index='Time', columns='Metric', values='Count', aggfunc='sum'
                        ).fillna(0)
                        st.bar_chart(pivot)
                else:
                    st.info("No tracking data found for this time range. Metrics appear after emails are sent with the configuration set enabled.")

        except Exception as e:
            st.error(f"Failed to connect to CloudWatch: {str(e)}")


# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📧 Exam Email Sender")
    st.markdown("---")

    st.markdown("### 📊 Status")
    st.markdown(f"- **Students Loaded:** {len(st.session_state.students)}")
    st.markdown(f"- **Links Generated:** {'✅' if st.session_state.links_generated else '❌'}")
    st.markdown(f"- **Emails Sent:** {'✅' if st.session_state.emails_sent else '❌'}")

    if st.session_state.email_results:
        sent = len([r for r in st.session_state.email_results if r['email_status'] == 'sent'])
        failed = len([r for r in st.session_state.email_results if r['email_status'] == 'failed'])
        st.markdown(f"- **Sent:** {sent} ✅")
        st.markdown(f"- **Failed:** {failed} ❌")

    st.markdown("---")
    st.markdown("### ℹ️ Workflow")
    if st.session_state.skip_link_generation:
        st.markdown("""
        1. Configure email settings
        2. Upload student CSV/Excel
        3. Customize email template
        4. Send emails to students
        5. Download reports
        """)
    else:
        st.markdown("""
        1. Configure API & SMTP settings
        2. Upload student CSV/Excel
        3. Generate exam links via API
        4. Customize email template
        5. Send emails to students
        6. Download reports
        """)

    st.markdown("---")
    if st.button("🗑️ Clear All Data"):
        for key in ['students', 'students_with_links', 'failed_candidates', 'links_generated',
                     'emails_sent', 'email_results', 'file_errors']:
            if key in st.session_state:
                if isinstance(st.session_state[key], list):
                    st.session_state[key] = []
                elif isinstance(st.session_state[key], bool):
                    st.session_state[key] = False
        st.rerun()

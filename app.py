"""Main Streamlit Application - Exam Portal Email Sender"""

import streamlit as st
import pandas as pd
from datetime import datetime, time as dt_time
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.file_handler import FileHandler
from modules.api_client import APIClient
from modules.email_sender import EmailSender
from modules.template_manager import TemplateManager
from modules.calendar_event import CalendarEvent
from modules.visual_editor import visual_editor
from config.settings import Config

# Page configuration
st.set_page_config(
    page_title="Exam Portal Email Sender",
    page_icon="📧",
    layout="wide"
)

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
        'email_subject': 'Invitation to Online Assessment | TAM – Digital Banking | 26 February',
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
        # Manual input rows
        'manual_entry_rows': [{'name': '', 'email': ''}],
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
    tab1, tab2, tab4, tab5, tab6 = st.tabs([
        "1️⃣ Email Settings",
        "2️⃣ Upload Data",
        "3️⃣ Email Template",
        "4️⃣ Send Emails",
        "5️⃣ Reports"
    ])
    tab3 = None  # No generate links tab
else:
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "1️⃣ API Parameters",
        "2️⃣ Upload Data",
        "3️⃣ Generate Links",
        "4️⃣ Email Template",
        "5️⃣ Send Emails",
        "6️⃣ Reports"
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
            help="File must have 'Name' and 'Email' columns"
        )

        if uploaded_file is not None:
            with st.spinner("Processing file..."):
                students, errors = FileHandler.process_file(uploaded_file)

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
        st.markdown("Enter student **Name** and **Email** below. Click ➕ to add more rows.")

        rows = st.session_state.manual_entry_rows

        for idx in range(len(rows)):
            col_name, col_email, col_del = st.columns([3, 4, 1])
            with col_name:
                rows[idx]['name'] = st.text_input(
                    "Name", value=rows[idx]['name'],
                    key=f"manual_name_{idx}",
                    placeholder="e.g. Alice Smith",
                    label_visibility="collapsed" if idx > 0 else "visible"
                )
            with col_email:
                rows[idx]['email'] = st.text_input(
                    "Email", value=rows[idx]['email'],
                    key=f"manual_email_{idx}",
                    placeholder="e.g. alice@example.com",
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
            rows.append({'name': '', 'email': ''})
            st.rerun()

        st.markdown("---")

        if st.button("✅ Load Entries", type="primary"):
            manual_students = []
            manual_errors = []
            seen_emails = set()

            for i, row in enumerate(rows, start=1):
                name = row['name'].strip()
                email = row['email'].strip().lower()

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
                manual_students.append({'name': name, 'email': email})

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

        # Template selector dropdown
        available_templates = TemplateManager.list_templates()
        if available_templates:
            template_names = [t['name'] for t in available_templates]
            selected_template = st.selectbox(
                "📄 Select Template",
                options=template_names,
                index=None,
                placeholder="Choose a template...",
                help="Pick a saved template to load into the editor.",
            )
            if selected_template:
                chosen = next(t for t in available_templates if t['name'] == selected_template)
                loaded_html = TemplateManager.load_template(chosen['filename'])
                if loaded_html != st.session_state.email_template:
                    st.session_state.email_template = loaded_html
                    st.session_state.template_editor_key += 1
                    st.rerun()

        # Custom program name override
        custom_program_name = st.text_input(
            "Program Name (override)",
            value=st.session_state.custom_program_name,
            help="Set a custom program name to replace {program_name} in subject & template. Leave empty to use the name from API.",
            placeholder="e.g. Software Engineering Assessment"
        )
        st.session_state.custom_program_name = custom_program_name

        # Email subject
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

        # Reset to default
        if st.button("🔄 Reset to Default Template"):
            if st.session_state.skip_link_generation:
                st.session_state.email_template = TemplateManager.get_general_email_template()
                st.session_state.email_subject = 'Invitation to Online Assessment | TAM – Digital Banking | 26 February'
            else:
                st.session_state.email_template = TemplateManager.get_default_template()
                st.session_state.email_subject = 'Invitation to Online Assessment | TAM – Digital Banking | 26 February'
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

        # Available placeholders
        with st.expander("📌 Available Placeholders"):
            placeholders = TemplateManager.get_available_placeholders(
                st.session_state.get('skip_link_generation', False)
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
                st.session_state.get('skip_link_generation', False)
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
            # Prepare students without links — just name & email
            students_to_email = [
                {
                    'name': s['name'],
                    'email': s['email'],
                    'candidate_id': '',
                    'login_link': '',
                    'expires_at': '',
                    'program_name': st.session_state.custom_program_name or '',
                    'round_name': '',
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

                st.markdown("**Duration \*:**")
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

        if st.button("📨 Send All Emails", type="primary", disabled=not confirm):
            if not st.session_state.aws_access_key or not st.session_state.aws_secret_key:
                st.error("❌ Please configure AWS SES credentials in Tab 1.")
            else:
                ses_config = {
                    'aws_access_key': st.session_state.aws_access_key,
                    'aws_secret_key': st.session_state.aws_secret_key,
                    'aws_region': st.session_state.aws_region,
                    'sender_email': st.session_state.sender_email,
                    'sender_name': st.session_state.sender_name,
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

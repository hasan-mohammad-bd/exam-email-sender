"""Main Streamlit Application - Exam Portal Email Sender"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.file_handler import FileHandler
from modules.api_client import APIClient
from modules.email_sender import EmailSender
from modules.template_manager import TemplateManager
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
        'email_subject': '🎓 Your Exam Portal Access Link - {program_name}',
        'program_id': int(Config.DEFAULT_PROGRAM_ID) if Config.DEFAULT_PROGRAM_ID else 1,
        'round_id': int(Config.DEFAULT_ROUND_ID) if Config.DEFAULT_ROUND_ID else 1,
        'session_time': Config.DEFAULT_SESSION_TIME or '730h',
        'sender_email': Config.SENDER_EMAIL,
        'sender_name': Config.SENDER_NAME,
        'aws_access_key': Config.AWS_SES_ACCESS_KEY,
        'aws_secret_key': Config.AWS_SES_SECRET_KEY,
        'aws_region': Config.AWS_SES_REGION,
        'api_endpoint': Config.API_ENDPOINT,
        'api_key': Config.API_KEY,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()

# ─── Header ─────────────────────────────────────────────────────────────────
st.title("📧 Exam Portal Email Sender")
st.markdown("Automated tool for generating exam links and sending personalized emails to students.")
st.markdown("---")

# ─── Create tabs ─────────────────────────────────────────────────────────────
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
    st.markdown("Upload a CSV or Excel file containing student **Name** and **Email** columns.")

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
        if st.session_state.students:
            st.info(f"📄 Previously loaded: **{len(st.session_state.students)}** student(s)")
            preview_df = pd.DataFrame(st.session_state.students)
            st.dataframe(preview_df, use_container_width=True, height=200)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: Generate Links
# ═══════════════════════════════════════════════════════════════════════════════
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

        # Email subject
        email_subject = st.text_input(
            "Email Subject",
            value=st.session_state.email_subject,
            help="You can use placeholders like {program_name}, {name}"
        )
        st.session_state.email_subject = email_subject

        # Template editor
        email_template = st.text_area(
            "HTML Email Template",
            value=st.session_state.email_template,
            height=500,
            help="Edit the HTML template. Use placeholders for dynamic content."
        )
        st.session_state.email_template = email_template

        # Reset to default
        if st.button("🔄 Reset to Default Template"):
            st.session_state.email_template = TemplateManager.get_default_template()
            st.session_state.email_subject = '🎓 Your Exam Portal Access Link - {program_name}'
            st.rerun()

    with col_preview:
        st.subheader("👁️ Preview")

        # Available placeholders
        with st.expander("📌 Available Placeholders"):
            placeholders = TemplateManager.get_available_placeholders()
            placeholder_df = pd.DataFrame(placeholders)
            st.table(placeholder_df)

        # Preview with sample data
        st.markdown("**Email Preview (with sample data):**")
        sample_data = TemplateManager.get_sample_data()

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
    st.header("Step 5: Send Emails")

    if not st.session_state.links_generated:
        st.warning("⚠️ Please generate links first (Tab 3).")
    else:
        students_to_email = [s for s in st.session_state.students_with_links if s.get('login_link') not in (None, 'N/A', '')]

        if not students_to_email:
            st.warning("⚠️ No candidates with valid links to send emails to. Check the failed candidates list in Tab 3.")

        if st.session_state.failed_candidates:
            st.info(f"ℹ️ {len(st.session_state.failed_candidates)} candidate(s) were skipped (not found in exam portal). Only candidates with valid links will receive emails.")

        # Pre-send checklist
        st.subheader("📋 Pre-Send Checklist")

        check_col1, check_col2 = st.columns(2)
        with check_col1:
            st.markdown(f"✅ **Students to email:** {len(students_to_email)}")
            st.markdown(f"✅ **Links generated:** {st.session_state.links_generated}")
            st.markdown(f"✅ **Email template ready:** {'Yes' if st.session_state.email_template else 'No'}")

        with check_col2:
            st.markdown(f"📧 **Sender:** {st.session_state.sender_name} <{st.session_state.sender_email}>")
            st.markdown(f"☁️ **Service:** AWS SES ({st.session_state.aws_region})")
            st.markdown(f"📝 **Subject:** {st.session_state.email_subject}")
            st.markdown(f"⏱️ **Delay between emails:** {Config.DELAY_BETWEEN_EMAILS}s")

        st.markdown("---")

        # Email sending settings
        st.subheader("⚙️ Sending Settings")
        delay_between = st.slider(
            "Delay between emails (seconds)",
            min_value=0.5,
            max_value=10.0,
            value=float(Config.DELAY_BETWEEN_EMAILS),
            step=0.5,
            help="Time to wait between sending each email (to avoid rate limits)"
        )

        # Preview recipients
        with st.expander(f"👥 Preview Recipients ({len(students_to_email)})"):
            preview_df = pd.DataFrame(students_to_email)[['name', 'email', 'candidate_id', 'login_link']]
            st.dataframe(preview_df, use_container_width=True)

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

                    # Send emails
                    results = email_sender.send_bulk_emails(
                        students=students_to_email,
                        subject=st.session_state.email_subject,
                        html_template=st.session_state.email_template,
                        delay=delay_between,
                        progress_callback=progress_callback
                    )

                    st.session_state.email_results = results
                    st.session_state.emails_sent = True

                    # Final summary
                    st.markdown("---")
                    st.subheader("📊 Sending Complete!")

                    summary_col1, summary_col2, summary_col3 = st.columns(3)
                    with summary_col1:
                        st.metric("Total Emails", len(results))
                    with summary_col2:
                        st.metric("Successfully Sent", counts['sent'])
                    with summary_col3:
                        st.metric("Failed", counts['failed'])

                    if counts['failed'] > 0:
                        st.warning("Some emails failed to send. Check the Reports tab for details.")

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

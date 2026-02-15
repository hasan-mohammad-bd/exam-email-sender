# 📧 Exam Portal Email Sender

Automated tool for generating exam portal links via API and sending personalized emails to students using a Streamlit web interface.

## Features

- **CSV/Excel Upload**: Import student data (Name, Email) from CSV or Excel files
- **API Integration**: Generate unique exam portal login links via API
- **Email Templates**: Customizable HTML email templates with placeholder support
- **Bulk Email Sending**: Send personalized emails via SMTP with progress tracking
- **Reports**: Download detailed reports of link generation and email delivery

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
API_ENDPOINT=https://your-api-endpoint.com/api/generate-links
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
SENDER_NAME=Your Organization
```

> **Gmail Users:** Use an [App Password](https://support.google.com/accounts/answer/185833) instead of your regular password.

### 3. Run the Application

```bash
streamlit run app.py
```

## Workflow

1. **Configure** — Set API parameters and SMTP credentials (Tab 1)
2. **Upload** — Upload a CSV/Excel file with student Name and Email columns (Tab 2)
3. **Generate Links** — Call the API to generate unique exam login links (Tab 3)
4. **Customize Template** — Edit the HTML email template and preview (Tab 4)
5. **Send Emails** — Send personalized emails to all students (Tab 5)
6. **Download Reports** — View and download delivery reports (Tab 6)

## CSV/Excel Format

Your file must include these columns:

| Name          | Email              |
|---------------|--------------------|
| Alice Smith   | alice@example.com  |
| Bob Johnson   | bob@example.com    |

## Available Template Placeholders

| Placeholder        | Description           |
|--------------------|-----------------------|
| `{name}`           | Student name          |
| `{email}`          | Student email         |
| `{login_link}`     | Unique login URL      |
| `{candidate_id}`   | Candidate ID          |
| `{program_name}`   | Program name          |
| `{round_name}`     | Round name            |
| `{expires_at}`     | Link expiry time      |
| `{session_duration}`| Session duration      |

## Project Structure

```
exam-email-sender/
├── app.py                      # Main Streamlit application
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
├── .gitignore                  # Git ignore rules
├── README.md                   # This file
├── modules/
│   ├── __init__.py
│   ├── file_handler.py         # CSV/Excel processing
│   ├── api_client.py           # API integration
│   ├── email_sender.py         # Email sending via SMTP
│   └── template_manager.py     # Template management
├── config/
│   ├── __init__.py
│   └── settings.py             # App settings
└── templates/
    └── default_template.html   # Default email template
```

## License

MIT

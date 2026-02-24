"""Email sender module for sending personalized emails via AWS SES"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, List, Tuple, Optional
import time
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class EmailSender:

    def __init__(self, ses_config: Dict):
        """
        ses_config should contain:
        - aws_access_key, aws_secret_key, aws_region, sender_email, sender_name
        """
        self.aws_access_key = ses_config['aws_access_key']
        self.aws_secret_key = ses_config['aws_secret_key']
        self.aws_region = ses_config.get('aws_region', 'ap-south-1')
        self.sender_email = ses_config['sender_email']
        self.sender_name = ses_config.get('sender_name', 'Exam Portal')

        self.client = boto3.client(
            'ses',
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key,
            region_name=self.aws_region
        )

    def test_connection(self) -> Tuple[bool, str]:
        """Test AWS SES connection by verifying the sender identity"""
        try:
            response = self.client.get_send_quota()
            max_24hr = response.get('Max24HourSend', 0)
            sent_24hr = response.get('SentLast24Hours', 0)
            return True, (
                f"AWS SES connected! "
                f"Send quota: {sent_24hr:.0f}/{max_24hr:.0f} emails (last 24h)"
            )
        except NoCredentialsError:
            return False, "AWS credentials not found. Check your access key and secret key."
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            return False, f"AWS SES error ({error_code}): {error_msg}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def _build_raw_email(
        self,
        recipient_email: str,
        subject: str,
        html_body: str,
        cc_emails: Optional[List[str]] = None,
        ics_content: Optional[str] = None,
        ics_filename: str = "calendar_event.ics",
    ) -> str:
        """Build a raw MIME email string."""
        plain_text = re.sub(r'<[^>]+>', '', html_body)
        plain_text = re.sub(r'\s+', ' ', plain_text).strip()
        source = f"{self.sender_name} <{self.sender_email}>"

        if ics_content:
            msg = MIMEMultipart('mixed')
            body_part = MIMEMultipart('alternative')
            body_part.attach(MIMEText(plain_text, 'plain', 'utf-8'))
            body_part.attach(MIMEText(html_body, 'html', 'utf-8'))
            msg.attach(body_part)
            cal_part = MIMEText(ics_content, 'calendar', 'utf-8')
            cal_part.set_param('method', 'REQUEST')
            cal_part.add_header('Content-Disposition', 'attachment', filename=ics_filename)
            msg.attach(cal_part)
        else:
            msg = MIMEMultipart('alternative')
            msg.attach(MIMEText(plain_text, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        msg['Subject'] = subject
        msg['From'] = source
        msg['To'] = recipient_email
        if cc_emails:
            msg['Cc'] = ', '.join(cc_emails)

        return msg.as_string()

    def _send_raw(
        self,
        raw_message: str,
        destinations: List[str],
    ) -> Tuple[bool, str]:
        """Send a raw MIME message via SES."""
        source = f"{self.sender_name} <{self.sender_email}>"
        response = self.client.send_raw_email(
            Source=source,
            Destinations=destinations,
            RawMessage={'Data': raw_message},
        )
        message_id = response.get('MessageId', '')
        return True, message_id

    def _send_bcc_copies(
        self,
        recipient_email: str,
        subject: str,
        html_body: str,
        bcc_emails: List[str],
        ics_content: Optional[str] = None,
        ics_filename: str = "calendar_event.ics",
    ) -> List[Tuple[str, bool, str]]:
        """
        Send individual copies to each BCC recipient.
        Each BCC recipient receives their own email where they can see
        themselves in the 'To' header (alongside the original recipient).
        AWS SES strips the Bcc header, so this is the only way for
        BCC recipients to know they received a copy.
        """
        results = []
        for bcc_addr in bcc_emails:
            try:
                # Build a separate email for this BCC recipient
                # To header shows: "original_recipient, bcc_recipient (BCC)"
                bcc_to = f"{recipient_email}, {bcc_addr} (BCC)"
                raw = self._build_raw_email(
                    recipient_email=bcc_to,
                    subject=subject,
                    html_body=html_body,
                    ics_content=ics_content,
                    ics_filename=ics_filename,
                )
                ok, mid = self._send_raw(raw, [bcc_addr])
                results.append((bcc_addr, ok, f"BCC copy sent (MessageId: {mid})"))
            except Exception as e:
                results.append((bcc_addr, False, f"BCC copy failed for {bcc_addr}: {e}"))
        return results

    def send_email(
        self,
        recipient_email: str,
        subject: str,
        html_body: str,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None,
    ) -> Tuple[bool, str]:
        """Send a single email via AWS SES using send_raw_email."""
        try:
            # Build and send the main email (To + CC)
            raw = self._build_raw_email(
                recipient_email=recipient_email,
                subject=subject,
                html_body=html_body,
                cc_emails=cc_emails,
            )
            destinations = [recipient_email]
            if cc_emails:
                destinations.extend(cc_emails)

            ok, message_id = self._send_raw(raw, destinations)

            # Send individual copies to BCC recipients
            if bcc_emails:
                self._send_bcc_copies(
                    recipient_email=recipient_email,
                    subject=subject,
                    html_body=html_body,
                    bcc_emails=bcc_emails,
                )

            return True, f"Email sent (MessageId: {message_id})"

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            if error_code == 'MessageRejected':
                return False, f"Email rejected: {error_msg}"
            elif error_code == 'MailFromDomainNotVerified':
                return False, f"Sender domain not verified: {error_msg}"
            else:
                return False, f"AWS SES error ({error_code}): {error_msg}"
        except Exception as e:
            return False, f"Error sending email: {str(e)}"

    def send_email_with_ics(
        self,
        recipient_email: str,
        subject: str,
        html_body: str,
        ics_content: str,
        ics_filename: str = "calendar_event.ics",
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None,
    ) -> Tuple[bool, str]:
        """Send an email with an ICS calendar attachment via AWS SES send_raw_email."""
        try:
            # Build and send the main email (To + CC)
            raw = self._build_raw_email(
                recipient_email=recipient_email,
                subject=subject,
                html_body=html_body,
                cc_emails=cc_emails,
                ics_content=ics_content,
                ics_filename=ics_filename,
            )
            destinations = [recipient_email]
            if cc_emails:
                destinations.extend(cc_emails)

            ok, message_id = self._send_raw(raw, destinations)

            # Send individual copies to BCC recipients
            if bcc_emails:
                self._send_bcc_copies(
                    recipient_email=recipient_email,
                    subject=subject,
                    html_body=html_body,
                    bcc_emails=bcc_emails,
                    ics_content=ics_content,
                    ics_filename=ics_filename,
                )

            return True, f"Email with calendar invite sent (MessageId: {message_id})"

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            return False, f"AWS SES error ({error_code}): {error_msg}"
        except Exception as e:
            return False, f"Error sending email: {str(e)}"

    def send_bulk_emails(
        self,
        students: List[Dict],
        subject: str,
        html_template: str,
        delay: float = 1.0,
        progress_callback=None,
        calendar_event_config: Optional[Dict] = None,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Send emails to multiple recipients via AWS SES.

        For each student:
        1. Replace placeholders in template
        2. Send email (with ICS attachment if calendar_event_config is provided)
        3. Update student dict with email_status
        4. Call progress_callback if provided
        5. Add delay between emails

        calendar_event_config keys:
            event_type, title, date_str, start_time_str, duration_str,
            organizer_name, organizer_email, location, meeting_link, description
        """
        from modules.calendar_event import CalendarEvent

        results = []

        for i, student in enumerate(students):
            # Replace placeholders in the template
            personalized_html = self._replace_placeholders(html_template, student)
            personalized_subject = self._replace_placeholders(subject, student)

            # Attempt to send
            if calendar_event_config:
                # Generate personalized ICS for this student
                ics_content, ics_error = CalendarEvent.generate_ics(
                    event_type=calendar_event_config.get('event_type', CalendarEvent.EVENT_TYPE_GOOGLE),
                    title=calendar_event_config.get('title', 'Exam Session'),
                    date_str=calendar_event_config.get('date_str', ''),
                    start_time_str=calendar_event_config.get('start_time_str', ''),
                    duration_str=calendar_event_config.get('duration_str', '1 hour'),
                    organizer_name=calendar_event_config.get('organizer_name', self.sender_name),
                    organizer_email=calendar_event_config.get('organizer_email', self.sender_email),
                    attendee_name=student.get('name', ''),
                    attendee_email=student.get('email', ''),
                    location=calendar_event_config.get('location', ''),
                    meeting_link=calendar_event_config.get('meeting_link', ''),
                    description=calendar_event_config.get('description', ''),
                )

                if ics_error or not ics_content:
                    success, message = False, f"Calendar event generation failed: {ics_error}"
                else:
                    event_type = calendar_event_config.get('event_type', CalendarEvent.EVENT_TYPE_GOOGLE)
                    ics_filename = (
                        "google_meet_event.ics"
                        if event_type == CalendarEvent.EVENT_TYPE_GOOGLE
                        else "outlook_meeting.ics"
                    )
                    success, message = self.send_email_with_ics(
                        recipient_email=student['email'],
                        subject=personalized_subject,
                        html_body=personalized_html,
                        ics_content=ics_content,
                        ics_filename=ics_filename,
                        cc_emails=cc_emails,
                        bcc_emails=bcc_emails,
                    )
            else:
                success, message = self.send_email(
                    recipient_email=student['email'],
                    subject=personalized_subject,
                    html_body=personalized_html,
                    cc_emails=cc_emails,
                    bcc_emails=bcc_emails,
                )

            # Update student record
            student_result = student.copy()
            student_result['email_status'] = 'sent' if success else 'failed'
            student_result['email_message'] = message
            student_result['send_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
            results.append(student_result)

            # Progress callback
            if progress_callback:
                progress_callback(i + 1, len(students), student['email'], success, message)

            # Delay between emails (skip after the last one)
            if i < len(students) - 1:
                time.sleep(delay)

        return results

    @staticmethod
    def _replace_placeholders(text: str, data: Dict) -> str:
        """Replace {placeholder} with actual values"""
        replacements = {
            '{name}': str(data.get('name', '')),
            '{email}': str(data.get('email', '')),
            '{login_link}': str(data.get('login_link', '')),
            '{candidate_id}': str(data.get('candidate_id', '')),
            '{program_name}': str(data.get('program_name', '')),
            '{round_name}': str(data.get('round_name', '')),
            '{expires_at}': str(data.get('expires_at', '')),
            '{session_duration}': str(data.get('session_duration', '')),
        }

        result = text
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)

        return result

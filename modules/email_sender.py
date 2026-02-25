"""Email sender module for sending personalized emails via AWS SES"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, List, Tuple, Optional
import time
import re
import json
import os
import csv
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Directory for checkpoints and crash reports
CHECKPOINT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports')


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

    def send_email(
        self,
        recipient_email: str,
        subject: str,
        html_body: str
    ) -> Tuple[bool, str]:
        """Send a single email via AWS SES"""
        try:
            # Create plain text version by stripping HTML
            plain_text = re.sub(r'<[^>]+>', '', html_body)
            plain_text = re.sub(r'\s+', ' ', plain_text).strip()

            source = f"{self.sender_name} <{self.sender_email}>"

            response = self.client.send_email(
                Source=source,
                Destination={
                    'ToAddresses': [recipient_email],
                },
                Message={
                    'Subject': {
                        'Data': subject,
                        'Charset': 'UTF-8',
                    },
                    'Body': {
                        'Text': {
                            'Data': plain_text,
                            'Charset': 'UTF-8',
                        },
                        'Html': {
                            'Data': html_body,
                            'Charset': 'UTF-8',
                        },
                    },
                },
            )

            message_id = response.get('MessageId', '')
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
    ) -> Tuple[bool, str]:
        """Send an email with an ICS calendar attachment via AWS SES send_raw_email."""
        try:
            plain_text = re.sub(r'<[^>]+>', '', html_body)
            plain_text = re.sub(r'\s+', ' ', plain_text).strip()

            source = f"{self.sender_name} <{self.sender_email}>"

            # Build MIME message
            msg = MIMEMultipart('mixed')
            msg['Subject'] = subject
            msg['From'] = source
            msg['To'] = recipient_email

            # Attach HTML + plain text as alternatives
            body_part = MIMEMultipart('alternative')
            body_part.attach(MIMEText(plain_text, 'plain', 'utf-8'))
            body_part.attach(MIMEText(html_body, 'html', 'utf-8'))
            msg.attach(body_part)

            # Attach ICS file — use MIMEText so encoding is handled correctly (no duplicate headers)
            cal_part = MIMEText(ics_content, 'calendar', 'utf-8')
            cal_part.set_param('method', 'REQUEST')
            cal_part.add_header('Content-Disposition', 'attachment', filename=ics_filename)
            msg.attach(cal_part)

            response = self.client.send_raw_email(
                Source=source,
                Destinations=[recipient_email],
                RawMessage={'Data': msg.as_string()},
            )

            message_id = response.get('MessageId', '')
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
        checkpoint_interval: int = 10,
        resume_from_checkpoint: bool = False,
    ) -> List[Dict]:
        """
        Send emails to multiple recipients via AWS SES with crash resilience.

        Features:
        - Saves checkpoint to disk every `checkpoint_interval` emails
        - On crash, auto-generates a partial report CSV
        - Can resume from last checkpoint if `resume_from_checkpoint` is True
        - Each email send is wrapped in try/except to prevent single failures from crashing the loop

        For each student:
        1. Replace placeholders in template
        2. Send email (with ICS attachment if calendar_event_config is provided)
        3. Update student dict with email_status
        4. Call progress_callback if provided
        5. Save checkpoint periodically
        6. Add delay between emails

        calendar_event_config keys:
            event_type, title, date_str, start_time_str, duration_str,
            organizer_name, organizer_email, location, meeting_link, description
        """
        from modules.calendar_event import CalendarEvent

        # Ensure reports directory exists
        os.makedirs(CHECKPOINT_DIR, exist_ok=True)

        # Generate session ID for this send operation
        session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        checkpoint_file = os.path.join(CHECKPOINT_DIR, f'checkpoint_{session_id}.json')

        results = []
        start_index = 0

        # Resume from checkpoint if requested
        if resume_from_checkpoint:
            checkpoint_data = self._load_latest_checkpoint()
            if checkpoint_data:
                results = checkpoint_data.get('results', [])
                start_index = checkpoint_data.get('next_index', 0)
                session_id = checkpoint_data.get('session_id', session_id)
                checkpoint_file = checkpoint_data.get('checkpoint_file', checkpoint_file)
                # Notify via callback about already-sent emails
                if progress_callback and results:
                    sent_count = len([r for r in results if r['email_status'] == 'sent'])
                    failed_count = len([r for r in results if r['email_status'] == 'failed'])
                    progress_callback(
                        start_index, len(students),
                        f"(resumed — {start_index} already processed)",
                        True,
                        f"Resuming: {sent_count} sent, {failed_count} failed previously"
                    )

        # Save initial checkpoint with all students marked pending
        self._save_checkpoint(checkpoint_file, {
            'session_id': session_id,
            'checkpoint_file': checkpoint_file,
            'total_students': len(students),
            'next_index': start_index,
            'results': results,
            'started_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'in_progress',
        })

        try:
            for i in range(start_index, len(students)):
                student = students[i]

                try:
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
                            )
                    else:
                        success, message = self.send_email(
                            recipient_email=student['email'],
                            subject=personalized_subject,
                            html_body=personalized_html,
                        )

                except Exception as e:
                    # Catch any unexpected error for THIS email, don't crash the whole loop
                    success = False
                    message = f"Unexpected error: {str(e)}"

                # Update student record
                student_result = student.copy()
                student_result['email_status'] = 'sent' if success else 'failed'
                student_result['email_message'] = message
                student_result['send_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
                results.append(student_result)

                # Progress callback
                if progress_callback:
                    progress_callback(i + 1, len(students), student['email'], success, message)

                # Save checkpoint every N emails
                if (i + 1) % checkpoint_interval == 0 or (i + 1) == len(students):
                    self._save_checkpoint(checkpoint_file, {
                        'session_id': session_id,
                        'checkpoint_file': checkpoint_file,
                        'total_students': len(students),
                        'next_index': i + 1,
                        'results': results,
                        'started_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'status': 'in_progress',
                    })

                # Delay between emails (skip after the last one)
                if i < len(students) - 1:
                    time.sleep(delay)

        except Exception as e:
            # CRASH HANDLER: save whatever we have so far
            crash_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            sent_count = len([r for r in results if r['email_status'] == 'sent'])
            failed_count = len([r for r in results if r['email_status'] == 'failed'])
            remaining = len(students) - len(results)

            # Mark remaining students as 'not_sent'
            for j in range(len(results), len(students)):
                student_result = students[j].copy()
                student_result['email_status'] = 'not_sent'
                student_result['email_message'] = f'Process crashed at email {len(results)}/{len(students)}'
                student_result['send_time'] = ''
                results.append(student_result)

            # Save crash checkpoint
            self._save_checkpoint(checkpoint_file, {
                'session_id': session_id,
                'checkpoint_file': checkpoint_file,
                'total_students': len(students),
                'next_index': len(results) - remaining,  # Resume point
                'results': results[:len(results) - remaining],  # Only actually processed
                'started_at': crash_time,
                'status': 'crashed',
                'crash_error': str(e),
            })

            # Auto-generate crash report CSV
            self._generate_crash_report(results, session_id, str(e), sent_count, failed_count, remaining)

            # Re-raise so the caller knows about the crash but results are saved
            raise

        # Completed successfully — update checkpoint status and clean up
        self._save_checkpoint(checkpoint_file, {
            'session_id': session_id,
            'checkpoint_file': checkpoint_file,
            'total_students': len(students),
            'next_index': len(students),
            'results': results,
            'started_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'completed',
        })

        # Auto-generate completion report
        self._generate_completion_report(results, session_id)

        return results

    # ─── Checkpoint & Recovery Methods ────────────────────────────────────────

    @staticmethod
    def _save_checkpoint(filepath: str, data: dict):
        """Save checkpoint data to a JSON file atomically."""
        temp_path = filepath + '.tmp'
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            # Atomic rename to prevent corruption
            os.replace(temp_path, filepath)
        except Exception:
            # If we can't save checkpoint, don't crash the email loop
            pass

    @staticmethod
    def _load_latest_checkpoint() -> Optional[Dict]:
        """Load the most recent checkpoint file that is resumable (in_progress or crashed)."""
        os.makedirs(CHECKPOINT_DIR, exist_ok=True)
        checkpoint_files = sorted(
            [f for f in os.listdir(CHECKPOINT_DIR) if f.startswith('checkpoint_') and f.endswith('.json')],
            reverse=True
        )
        for fname in checkpoint_files:
            try:
                fpath = os.path.join(CHECKPOINT_DIR, fname)
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if data.get('status') in ('in_progress', 'crashed'):
                    data['checkpoint_file'] = fpath
                    return data
            except Exception:
                continue
        return None

    @staticmethod
    def get_resumable_session() -> Optional[Dict]:
        """Public method to check if there's a resumable session. Returns summary info."""
        data = EmailSender._load_latest_checkpoint()
        if not data:
            return None

        results = data.get('results', [])
        total = data.get('total_students', 0)
        processed = data.get('next_index', 0)
        sent = len([r for r in results if r.get('email_status') == 'sent'])
        failed = len([r for r in results if r.get('email_status') == 'failed'])

        return {
            'session_id': data.get('session_id', ''),
            'total': total,
            'processed': processed,
            'remaining': total - processed,
            'sent': sent,
            'failed': failed,
            'status': data.get('status', 'unknown'),
            'started_at': data.get('started_at', ''),
            'crash_error': data.get('crash_error', ''),
            'checkpoint_file': data.get('checkpoint_file', ''),
        }

    @staticmethod
    def clear_checkpoint(checkpoint_file: str = None):
        """Mark a checkpoint as cleared/completed so it won't be picked up for resume."""
        if checkpoint_file and os.path.exists(checkpoint_file):
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                data['status'] = 'cleared'
                with open(checkpoint_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    @staticmethod
    def _generate_crash_report(results: List[Dict], session_id: str, error: str,
                                sent_count: int, failed_count: int, remaining: int):
        """Generate a CSV crash report so data is never lost."""
        os.makedirs(CHECKPOINT_DIR, exist_ok=True)
        readable_time = datetime.now().strftime('%d %b %Y %I-%M %p')
        report_path = os.path.join(CHECKPOINT_DIR, f'Crash Report - {readable_time}.csv')
        try:
            if results:
                keys = results[0].keys()
                with open(report_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=keys)
                    writer.writeheader()
                    writer.writerows(results)

            # Also write a summary text file
            summary_path = os.path.join(CHECKPOINT_DIR, f'Crash Summary - {readable_time}.txt')
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(f"═══ EMAIL SENDING CRASH REPORT ═══\n")
                f.write(f"Session ID: {session_id}\n")
                f.write(f"Crash Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Error: {error}\n")
                f.write(f"──────────────────────────────────\n")
                f.write(f"Total Emails: {sent_count + failed_count + remaining}\n")
                f.write(f"Successfully Sent: {sent_count}\n")
                f.write(f"Failed: {failed_count}\n")
                f.write(f"Not Sent (remaining): {remaining}\n")
                f.write(f"──────────────────────────────────\n")
                f.write(f"CSV Report: {report_path}\n")
                f.write(f"You can RESUME sending from where it stopped.\n")
        except Exception:
            pass

    @staticmethod
    def _generate_completion_report(results: List[Dict], session_id: str):
        """Generate a CSV report on successful completion."""
        os.makedirs(CHECKPOINT_DIR, exist_ok=True)
        readable_time = datetime.now().strftime('%d %b %Y %I-%M %p')
        report_path = os.path.join(CHECKPOINT_DIR, f'Email Report - {readable_time}.csv')
        try:
            if results:
                keys = results[0].keys()
                with open(report_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=keys)
                    writer.writeheader()
                    writer.writerows(results)
        except Exception:
            pass

    @staticmethod
    def _replace_placeholders(text: str, data: Dict) -> str:
        """Replace {placeholder} with actual values"""
        replacements = {
            '{name}': str(data.get('name', '')),
            '{email}': str(data.get('email', '')),
            '{login_id}': str(data.get('login_id', '')),
            '{password}': str(data.get('password', '')),
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

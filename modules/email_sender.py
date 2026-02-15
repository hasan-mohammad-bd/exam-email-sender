"""Email sender module for sending personalized emails via AWS SES"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, List, Tuple
import time
import re


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

    def send_bulk_emails(
        self,
        students: List[Dict],
        subject: str,
        html_template: str,
        delay: float = 1.0,
        progress_callback=None
    ) -> List[Dict]:
        """
        Send emails to multiple recipients via AWS SES.

        For each student:
        1. Replace placeholders in template
        2. Send email
        3. Update student dict with email_status
        4. Call progress_callback if provided
        5. Add delay between emails
        """
        results = []

        for i, student in enumerate(students):
            # Replace placeholders in the template
            personalized_html = self._replace_placeholders(html_template, student)
            personalized_subject = self._replace_placeholders(subject, student)

            # Attempt to send
            success, message = self.send_email(
                recipient_email=student['email'],
                subject=personalized_subject,
                html_body=personalized_html
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

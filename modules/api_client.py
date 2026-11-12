"""API client for generating exam portal links"""

import requests
from datetime import datetime, timezone
from typing import List, Dict, Tuple


class APIClient:

    @staticmethod
    def _format_expires_at(raw: str) -> str:
        """Convert ISO 8601 datetime (e.g. 2026-02-19T05:33:38.427Z) to a readable string."""
        if not raw or raw == 'N/A':
            return raw
        try:
            # Parse ISO 8601 with optional milliseconds and Z suffix
            dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
            return dt.strftime('%B %d, %Y at %I:%M %p UTC')
        except (ValueError, AttributeError):
            return raw

    def __init__(self, api_endpoint: str, api_key: str = '', timeout: int = 30):
        self.api_endpoint = api_endpoint
        self.api_key = api_key
        self.timeout = timeout

    def generate_links(
        self,
        emails: List[str],
        program_id: int,
        round_id: int,
        session_time: str
    ) -> Tuple[bool, Dict, str]:
        """
        Call API to generate unique links.

        Payload format:
        {
            "program_id": 6,
            "round_id": 6666,
            "session_time": "730h",
            "emails": ["email1@example.com", "email2@example.com"]
        }

        Returns: (success, response_data, error_message)
        """
        payload = {
            "program_id": program_id,
            "round_id": round_id,
            "session_time": session_time,
            "emails": emails,
        }

        try:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            if self.api_key:
                headers["x-api-key"] = self.api_key

            response = requests.post(
                self.api_endpoint,
                json=payload,
                timeout=self.timeout,
                headers=headers
            )

            if response.status_code != 200:
                return False, {}, f"API returned status code {response.status_code}: {response.text}"

            data = response.json()

            # Validate response structure
            if data.get('status') != 'ok':
                error_msg = data.get('message', 'Unknown API error')
                return False, {}, f"API error: {error_msg}"

            if 'data' not in data:
                return False, {}, "API response missing 'data' field"

            if 'generated_links' not in data['data']:
                return False, {}, "API response missing 'generated_links' field"

            return True, data, ""

        except requests.exceptions.Timeout:
            return False, {}, f"API request timed out after {self.timeout} seconds"
        except requests.exceptions.ConnectionError:
            return False, {}, "Could not connect to the API. Please check the endpoint URL."
        except requests.exceptions.JSONDecodeError:
            return False, {}, "API returned invalid JSON response"
        except Exception as e:
            return False, {}, f"Unexpected error: {str(e)}"

    @staticmethod
    def _clean_link(link):
        """Fix double-slash in the path part of a URL (keeps the scheme's //)."""
        if isinstance(link, str) and '://' in link:
            parts = link.split('://', 1)
            if len(parts) == 2:
                parts[1] = parts[1].replace('//', '/')
                link = '://'.join(parts)
        return link

    @staticmethod
    def _build_lookups(api_response: Dict) -> Tuple[Dict, Dict, Dict]:
        """
        Index an API response by lowercase email.

        Returns: (link_lookup, error_lookup, program_info)
        """
        response_data = api_response.get('data', {})
        generated_links = response_data.get('generated_links', [])
        program_info = response_data.get('program_info', {})
        api_errors = response_data.get('errors', [])

        error_lookup = {}
        for err in api_errors:
            err_email = err.get('email', '').strip().lower()
            if err_email:
                error_lookup[err_email] = err.get('error', 'Unknown error')

        link_lookup = {}
        for link_entry in generated_links:
            email_key = link_entry.get('email', '').strip().lower()
            if email_key:
                link_lookup[email_key] = link_entry

        return link_lookup, error_lookup, program_info

    @staticmethod
    def map_links_to_students(students: List[Dict], api_response: Dict) -> Tuple[List[Dict], List[Dict]]:
        """
        Map generated links back to student data.

        Returns:
            (successful_students, failed_candidates)
            - successful_students: students with valid links (will receive emails)
            - failed_candidates: students the API couldn't find (no email sent)
        """
        link_lookup, error_lookup, program_info = APIClient._build_lookups(api_response)

        program_name = program_info.get('program_name', 'N/A')
        round_name = program_info.get('round_name', 'N/A')

        successful_students = []
        failed_candidates = []

        for student in students:
            email = student['email'].strip().lower()

            # Check if this email failed in the API
            if email in error_lookup:
                failed_candidates.append({
                    'name': student['name'],
                    'email': student['email'],
                    'error': error_lookup.get(email, 'Candidate not found'),
                })
                continue

            link_data = link_lookup.get(email, {})

            # If no link data found and not in errors, still mark as failed
            if not link_data:
                failed_candidates.append({
                    'name': student['name'],
                    'email': student['email'],
                    'error': 'No link generated (email not matched)',
                })
                continue

            login_link = APIClient._clean_link(link_data.get('login_link', link_data.get('link', 'N/A')))

            enriched_student = {
                'name': student['name'],
                'email': student['email'],
                'candidate_id': link_data.get('candidate_id', 'N/A'),
                'login_link': login_link,
                'link_1': login_link,
                'link_2': '',
                'expires_at': APIClient._format_expires_at(link_data.get('expires_at', 'N/A')),
                'expires_at_2': '',
                'program_name': program_name,
                'round_name': round_name,
                'round_name_2': '',
                'login_id': student.get('login_id', ''),
                'password': student.get('password', ''),
                'email_status': 'pending',
            }
            successful_students.append(enriched_student)

        return successful_students, failed_candidates

    @staticmethod
    def merge_second_round(students_with_links: List[Dict], api_response: Dict) -> Tuple[List[Dict], List[Dict]]:
        """
        Add Round 2 links (link_2) onto students that already have a Round 1 link.

        Students are never dropped: if Round 2 has no link for a student, link_2
        stays blank and the student is reported in round2_failed.

        Returns:
            (students, round2_failed)
        """
        link_lookup, error_lookup, program_info = APIClient._build_lookups(api_response)
        round_name_2 = program_info.get('round_name', '')

        merged = []
        round2_failed = []

        for student in students_with_links:
            student = dict(student)
            email = student['email'].strip().lower()
            link_data = link_lookup.get(email, {})
            link_2 = link_data.get('login_link', link_data.get('link', '')) if link_data else ''

            if email in error_lookup or not link_2 or link_2 == 'N/A':
                student['link_2'] = ''
                student['round_name_2'] = ''
                student['expires_at_2'] = ''
                round2_failed.append({
                    'name': student['name'],
                    'email': student['email'],
                    'error': error_lookup.get(email, 'No Round 2 link generated (email not matched)'),
                })
            else:
                student['link_2'] = APIClient._clean_link(link_2)
                student['round_name_2'] = round_name_2
                student['expires_at_2'] = APIClient._format_expires_at(link_data.get('expires_at', ''))

            merged.append(student)

        return merged, round2_failed

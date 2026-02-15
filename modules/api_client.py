"""API client for generating exam portal links"""

import requests
from typing import List, Dict, Tuple


class APIClient:

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
    def map_links_to_students(students: List[Dict], api_response: Dict) -> Tuple[List[Dict], List[Dict]]:
        """
        Map generated links back to student data.

        Returns:
            (successful_students, failed_candidates)
            - successful_students: students with valid links (will receive emails)
            - failed_candidates: students the API couldn't find (no email sent)
        """
        response_data = api_response.get('data', {})
        generated_links = response_data.get('generated_links', [])
        program_info = response_data.get('program_info', {})
        api_errors = response_data.get('errors', [])

        program_name = program_info.get('program_name', 'N/A')
        round_name = program_info.get('round_name', 'N/A')

        # Build a set of failed emails from API errors
        failed_emails = set()
        error_lookup = {}
        for err in api_errors:
            err_email = err.get('email', '').strip().lower()
            if err_email:
                failed_emails.add(err_email)
                error_lookup[err_email] = err.get('error', 'Unknown error')

        # Build a lookup by email for generated links
        link_lookup = {}
        for link_entry in generated_links:
            email_key = link_entry.get('email', '').strip().lower()
            if email_key:
                link_lookup[email_key] = link_entry

        successful_students = []
        failed_candidates = []

        for student in students:
            email = student['email'].strip().lower()

            # Check if this email failed in the API
            if email in failed_emails:
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

            # Fix double-slash in login_link URL
            login_link = link_data.get('login_link', link_data.get('link', 'N/A'))
            if isinstance(login_link, str) and '://' in login_link:
                parts = login_link.split('://', 1)
                if len(parts) == 2:
                    parts[1] = parts[1].replace('//', '/')
                    login_link = '://'.join(parts)

            enriched_student = {
                'name': student['name'],
                'email': student['email'],
                'candidate_id': link_data.get('candidate_id', 'N/A'),
                'login_link': login_link,
                'expires_at': link_data.get('expires_at', 'N/A'),
                'program_name': program_name,
                'round_name': round_name,
                'email_status': 'pending',
            }
            successful_students.append(enriched_student)

        return successful_students, failed_candidates

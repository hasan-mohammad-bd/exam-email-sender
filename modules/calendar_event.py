"""Calendar event generator for Google Meet and Outlook calendar invites (.ics)"""

import re
import uuid
from datetime import datetime, timedelta
from typing import Optional


class CalendarEvent:
    """Generates ICS calendar event data compatible with Google Calendar and Outlook."""

    EVENT_TYPE_GOOGLE = "google_meet"
    EVENT_TYPE_OUTLOOK = "outlook"

    @staticmethod
    def _parse_datetime(date_str: str, time_str: str) -> Optional[datetime]:
        """
        Parse date and time from text strings.
        date_str: e.g. '2026-02-25' or '25/02/2026' or '25-02-2026'
        time_str: e.g. '10:00' or '10:00 AM' or '14:30'
        """
        date_str = date_str.strip()
        time_str = time_str.strip()

        # Normalize date separators
        date_str = date_str.replace('/', '-')

        # Try ISO format first
        date_formats = ['%Y-%m-%d', '%d-%m-%Y', '%m-%d-%Y']
        parsed_date = None
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                continue

        if parsed_date is None:
            return None

        # Normalize time
        time_str_clean = time_str.upper().strip()
        time_formats = ['%H:%M', '%I:%M %p', '%I:%M%p', '%H%M']
        parsed_time = None
        for fmt in time_formats:
            try:
                parsed_time = datetime.strptime(time_str_clean, fmt)
                break
            except ValueError:
                continue

        if parsed_time is None:
            return None

        return parsed_date.replace(
            hour=parsed_time.hour,
            minute=parsed_time.minute,
            second=0,
            microsecond=0
        )

    @staticmethod
    def _fold_line(line: str) -> str:
        """
        Fold a single ICS property line per RFC 5545:
        lines longer than 75 octets are split with CRLF + single space.
        """
        # Work in bytes to respect octet limit
        encoded = line.encode('utf-8')
        if len(encoded) <= 75:
            return line
        result = b''
        # First chunk: 75 bytes
        result += encoded[:75] + b'\r\n '
        remaining = encoded[75:]
        # Subsequent chunks: 74 bytes each (1 byte used by the leading space)
        while len(remaining) > 74:
            result += remaining[:74] + b'\r\n '
            remaining = remaining[74:]
        result += remaining
        return result.decode('utf-8')

    @staticmethod
    def _escape_value(value: str) -> str:
        """Escape special characters in ICS property values per RFC 5545."""
        # Escape backslash first, then semicolons, commas, and newlines
        value = value.replace('\\', '\\\\')
        value = value.replace(';', '\\;')
        value = value.replace(',', '\\,')
        # Literal newlines become \n escape sequence
        value = value.replace('\r\n', '\\n').replace('\n', '\\n').replace('\r', '\\n')
        return value

    @staticmethod
    def _parse_duration_minutes(duration_str: str) -> int:
        """
        Parse duration string to minutes.
        e.g. '1 hour', '90 minutes', '1.5 hours', '2h', '30m', '1h 30m'
        """
        duration_str = duration_str.lower().strip()
        total_minutes = 0

        # Handle '1h 30m' or '1h30m' patterns
        hours_match = re.search(r'(\d+(?:\.\d+)?)\s*h(?:our|ours|r|rs)?', duration_str)
        mins_match = re.search(r'(\d+)\s*m(?:in|ins|inute|inutes)?', duration_str)

        if hours_match:
            total_minutes += int(float(hours_match.group(1)) * 60)
        if mins_match:
            total_minutes += int(mins_match.group(1))

        # Fallback: try plain number (assume minutes)
        if total_minutes == 0:
            plain_match = re.search(r'^(\d+)$', duration_str.strip())
            if plain_match:
                total_minutes = int(plain_match.group(1))

        return total_minutes if total_minutes > 0 else 60  # default 60 min

    @staticmethod
    def _format_dt(dt: datetime) -> str:
        """Format datetime to ICS format (local, no timezone suffix)."""
        return dt.strftime('%Y%m%dT%H%M%S')

    @classmethod
    def generate_ics(
        cls,
        event_type: str,
        title: str,
        date_str: str,
        start_time_str: str,
        duration_str: str,
        organizer_name: str,
        organizer_email: str,
        attendee_name: str,
        attendee_email: str,
        location: str = '',
        meeting_link: str = '',
        description: str = '',
    ) -> tuple:
        """
        Generate an ICS calendar event string.

        Returns:
            (ics_content: str, error: str | None)
        """
        start_dt = cls._parse_datetime(date_str, start_time_str)
        if start_dt is None:
            return None, f"Could not parse date '{date_str}' or time '{start_time_str}'. Use format: YYYY-MM-DD and HH:MM"

        duration_mins = cls._parse_duration_minutes(duration_str)
        end_dt = start_dt + timedelta(minutes=duration_mins)

        uid = str(uuid.uuid4())
        # DTSTAMP must be UTC (RFC 5545)
        dtstamp_str = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        start_str = cls._format_dt(start_dt)
        end_str = cls._format_dt(end_dt)

        # Build description with meeting link (ICS \n escape for newlines)
        desc_parts = []
        if description:
            desc_parts.append(cls._escape_value(description))
        if meeting_link:
            desc_parts.append(f'Meeting Link: {meeting_link}')
        full_description = '\\n\\n'.join(desc_parts) if desc_parts else ''

        full_location = location or meeting_link or ''

        # Quote the CN parameter if it contains special characters
        def _cn(name: str) -> str:
            if any(c in name for c in (',', ';', ':', '"')):
                return f'"{name}"'
            return name

        # Build raw property lines (will be folded below)
        raw_lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Exam Portal Email Sender//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:REQUEST",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{dtstamp_str}",
            f"DTSTART:{start_str}",
            f"DTEND:{end_str}",
            f"SUMMARY:{cls._escape_value(title)}",
            f"DESCRIPTION:{full_description}",
            f"LOCATION:{cls._escape_value(full_location)}",
            f"ORGANIZER;CN={_cn(organizer_name)}:MAILTO:{organizer_email}",
            f"ATTENDEE;CN={_cn(attendee_name)};ROLE=REQ-PARTICIPANT;RSVP=TRUE:MAILTO:{attendee_email}",
            "STATUS:CONFIRMED",
            "SEQUENCE:0",
            "TRANSP:OPAQUE",
        ]

        if event_type == cls.EVENT_TYPE_GOOGLE and meeting_link:
            raw_lines.append(f"X-GOOGLE-CONFERENCE:{meeting_link}")

        if event_type == cls.EVENT_TYPE_OUTLOOK:
            raw_lines += [
                "X-MICROSOFT-CDO-BUSYSTATUS:BUSY",
                "X-MICROSOFT-CDO-IMPORTANCE:1",
                "X-MS-OLK-ALLOWEXTERNCHECK:TRUE",
            ]

        raw_lines += [
            "END:VEVENT",
            "END:VCALENDAR",
        ]

        # Fold each line per RFC 5545 and join with CRLF
        folded_lines = [cls._fold_line(line) for line in raw_lines]
        ics_content = "\r\n".join(folded_lines) + "\r\n"
        return ics_content, None

    @classmethod
    def get_event_type_label(cls, event_type: str) -> str:
        labels = {
            cls.EVENT_TYPE_GOOGLE: "Google Meet",
            cls.EVENT_TYPE_OUTLOOK: "Outlook / Microsoft Teams",
        }
        return labels.get(event_type, event_type)

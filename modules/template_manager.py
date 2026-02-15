"""Template manager for email templates"""

import os
from typing import List, Dict


class TemplateManager:

    @staticmethod
    def get_default_template() -> str:
        """Return default HTML email template"""
        # Try to load from file first
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'templates',
            'default_template.html'
        )
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()

        # Fallback inline template
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f4f4f4;
        }
        .container {
            background: #ffffff;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 24px;
        }
        .content {
            padding: 30px;
        }
        .button {
            display: inline-block;
            padding: 15px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin: 20px 0;
            font-weight: bold;
            font-size: 16px;
        }
        .button:hover {
            opacity: 0.9;
        }
        .info-box {
            background: #f8f9fa;
            padding: 20px;
            border-left: 4px solid #667eea;
            margin: 20px 0;
            border-radius: 0 5px 5px 0;
        }
        .info-box h3 {
            margin-top: 0;
            color: #667eea;
        }
        .info-box ul {
            list-style: none;
            padding: 0;
        }
        .info-box ul li {
            padding: 5px 0;
            border-bottom: 1px solid #eee;
        }
        .info-box ul li:last-child {
            border-bottom: none;
        }
        .footer {
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            font-size: 12px;
            color: #888;
        }
        .instructions {
            background: #fff3cd;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .instructions h3 {
            margin-top: 0;
            color: #856404;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎓 Exam Portal Access</h1>
            <p style="margin: 5px 0 0 0; opacity: 0.9;">Your exam link is ready</p>
        </div>

        <div class="content">
            <p>Dear <strong>{name}</strong>,</p>

            <p>Your exam portal link for <strong>{program_name}</strong> has been generated.
            Please use the button below to access your exam.</p>

            <center>
                <a href="{login_link}" class="button">🔗 Access Exam Portal</a>
            </center>

            <div class="info-box">
                <h3>📋 Exam Details</h3>
                <ul>
                    <li><strong>Candidate ID:</strong> {candidate_id}</li>
                    <li><strong>Program:</strong> {program_name}</li>
                    <li><strong>Round:</strong> {round_name}</li>
                    <li><strong>Link Expires:</strong> {expires_at}</li>
                </ul>
            </div>

            <div class="instructions">
                <h3>⚠️ Important Instructions</h3>
                <ul>
                    <li>This link is unique to you — do not share it with anyone.</li>
                    <li>Ensure a stable internet connection before starting.</li>
                    <li>Use a modern browser (Chrome, Firefox, or Edge).</li>
                    <li>Complete the exam before the expiry time.</li>
                </ul>
            </div>

            <p>If you have any questions, please contact the recruitment team.</p>

            <p>Best regards,<br><strong>Recruitment Team</strong></p>
        </div>

        <div class="footer">
            <p>This is an automated email. Please do not reply directly.</p>
        </div>
    </div>
</body>
</html>"""

    @staticmethod
    def get_available_placeholders() -> List[Dict[str, str]]:
        """Return list of available placeholders"""
        return [
            {'placeholder': '{name}', 'description': 'Student name'},
            {'placeholder': '{email}', 'description': 'Student email'},
            {'placeholder': '{login_link}', 'description': 'Unique login URL'},
            {'placeholder': '{candidate_id}', 'description': 'Candidate ID'},
            {'placeholder': '{program_name}', 'description': 'Program name'},
            {'placeholder': '{round_name}', 'description': 'Round name'},
            {'placeholder': '{expires_at}', 'description': 'Link expiry time'},
            {'placeholder': '{session_duration}', 'description': 'Session duration'},
        ]

    @staticmethod
    def get_sample_data() -> Dict:
        """Return sample data for template preview"""
        return {
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'login_link': 'https://exam-portal.example.com/login/abc123',
            'candidate_id': '12345',
            'program_name': 'Software Engineering Assessment',
            'round_name': 'Technical Round 1',
            'expires_at': '2026-03-17 23:59:59',
            'session_duration': '730h',
        }

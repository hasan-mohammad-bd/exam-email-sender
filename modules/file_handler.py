"""Handle CSV and Excel file operations"""

import pandas as pd
import re
from typing import List, Dict, Tuple


class FileHandler:

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, str(email).strip()) is not None

    @staticmethod
    def read_file(file) -> pd.DataFrame:
        """Read CSV or Excel file"""
        filename = file.name.lower()

        if filename.endswith('.csv'):
            df = pd.read_csv(file)
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file)
        else:
            raise ValueError("Unsupported file format. Please upload CSV or Excel files.")

        return df

    @staticmethod
    def process_file(file) -> Tuple[List[Dict], List[str]]:
        """
        Process uploaded file and extract student data.
        Returns: (student_list, errors)
        """
        errors = []
        students = []

        try:
            df = FileHandler.read_file(file)
        except Exception as e:
            return [], [f"Error reading file: {str(e)}"]

        # Normalize column names: strip whitespace and lowercase
        df.columns = [col.strip().lower() for col in df.columns]

        # Map common column name variations
        column_mappings = {
            'name': ['name', 'student_name', 'full_name', 'student name', 'fullname', 'candidate_name', 'candidate name'],
            'email': ['email', 'email_address', 'e-mail', 'mail', 'email address', 'student_email', 'student email'],
        }

        resolved_columns = {}
        for target, options in column_mappings.items():
            found = False
            for option in options:
                if option in df.columns:
                    resolved_columns[target] = option
                    found = True
                    break
            if not found:
                errors.append(f"Required column '{target}' not found. Available columns: {list(df.columns)}")

        if errors:
            return [], errors

        # Rename columns to standard names
        df = df.rename(columns={v: k for k, v in resolved_columns.items()})

        # Drop rows where both name and email are missing
        df = df.dropna(subset=['name', 'email'], how='all')

        # Fill missing names with 'Unknown'
        df['name'] = df['name'].fillna('Unknown').astype(str).str.strip()

        # Clean email column
        df['email'] = df['email'].astype(str).str.strip().str.lower()

        # Remove duplicate emails
        duplicates = df[df.duplicated(subset=['email'], keep='first')]
        if len(duplicates) > 0:
            for _, row in duplicates.iterrows():
                errors.append(f"Duplicate email removed: {row['email']}")
            df = df.drop_duplicates(subset=['email'], keep='first')

        # Validate each email
        valid_students = []
        for idx, row in df.iterrows():
            email = row['email']
            name = row['name']

            if not email or email == 'nan' or email == '':
                errors.append(f"Row {idx + 2}: Empty email for '{name}'")
                continue

            if not FileHandler.validate_email(email):
                errors.append(f"Row {idx + 2}: Invalid email format '{email}'")
                continue

            valid_students.append({
                'name': name,
                'email': email,
            })

        if not valid_students:
            errors.append("No valid student records found in the file.")

        return valid_students, errors

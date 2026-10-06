"""Shared account and academic-program options for ConnectGuidance."""

# (stored value, display label, short code)
FSUU_PROGRAMS = [
    ('CITEC', 'College of Information, Technology, Entertainment, and Computing', 'CITEC'),
    ('CCJE', 'College of Criminal Justice Education', 'CCJE'),
    ('CTE', 'College of Teacher Education', 'CTE'),
    ('CoA', 'College of Accountancy', 'CoA'),
    ('CoN', 'College of Nursing', 'CoN'),
    ('CAS', 'College of Arts and Sciences', 'CAS'),
    ('CORE', 'College of Operations, Resources, and Entrepreneurship', 'CORE'),
    ('CEnTech', 'College of Engineering and Technology', 'CEnTech'),
    ('CIHT', 'College of Innovative Hospitality and Tourism', 'CIHT'),
]

# Two-item choices are suitable for Django form and template select fields.
FSUU_PROGRAM_CHOICES = [(code, name) for code, name, _ in FSUU_PROGRAMS]

# Seed fixtures are intentionally kept separate from the academic-program list.
COUNSELOR_SEED_ACCOUNTS = [
    {
        'username': 'counselor1', 'email': 'counselor@guidance.edu',
        'password': 'CounselorPassword123!', 'full_name': 'Prof. Marcus Thorne',
        'department': 'Psychological Services',
    },
    {
        'username': 'counselor2', 'email': 'counselor2@guidance.edu',
        'password': 'CounselorPassword123!', 'full_name': 'Dr. Sarah Jenkins',
        'department': 'Career & Academic Wellness',
    },
]

RECEPTIONIST_SEED_ACCOUNTS = [
    {
        'username': 'receptionist', 'email': 'receptionist@guidance.edu',
        'password': 'ReceptionPassword123!', 'full_name': 'Clara Oswald (Front Desk)',
        'department': 'Student Care Helpdesk',
    },
]

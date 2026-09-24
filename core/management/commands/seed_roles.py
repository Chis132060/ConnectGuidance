import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import Profile, Appointment, CaseNote, AuditLog, StudentMoodAlert
from core.choices import RoleChoices, AppointmentStatusChoices, ConcernTypeChoices
from core.services.encryption import encrypt_text


class Command(BaseCommand):
    help = "Seed test accounts and initial data for GuidanceConnect roles"

    def handle(self, *args, **options):
        self.stdout.write("Seeding GuidanceConnect test roles and initial fixtures...")

        accounts = [
            {
                "username": "admin",
                "email": "admin@guidance.edu",
                "password": "AdminPassword123!",
                "full_name": "Dr. Eleanor Vance (Lead Admin)",
                "role": RoleChoices.ADMIN,
                "department": "Guidance Administration",
                "student_id": None,
                "is_superuser": True,
                "is_staff": True
            },
            {
                "username": "counselor1",
                "email": "counselor@guidance.edu",
                "password": "CounselorPassword123!",
                "full_name": "Prof. Marcus Thorne",
                "role": RoleChoices.COUNSELOR,
                "department": "Psychological Services",
                "student_id": None,
                "is_superuser": False,
                "is_staff": False
            },
            {
                "username": "counselor2",
                "email": "counselor2@guidance.edu",
                "password": "CounselorPassword123!",
                "full_name": "Dr. Sarah Jenkins",
                "role": RoleChoices.COUNSELOR,
                "department": "Career & Academic Wellness",
                "student_id": None,
                "is_superuser": False,
                "is_staff": False
            },
            {
                "username": "receptionist",
                "email": "receptionist@guidance.edu",
                "password": "ReceptionPassword123!",
                "full_name": "Clara Oswald (Front Desk)",
                "role": RoleChoices.RECEPTIONIST,
                "department": "Student Care Helpdesk",
                "student_id": None,
                "is_superuser": False,
                "is_staff": False
            },
            {
                "username": "student1",
                "email": "student@university.edu",
                "password": "StudentPassword123!",
                "full_name": "Alex Mercer",
                "role": RoleChoices.STUDENT,
                "department": "Computer Science",
                "student_id": "2024-10021",
                "is_superuser": False,
                "is_staff": False
            },
            {
                "username": "student2",
                "email": "student2@university.edu",
                "password": "StudentPassword123!",
                "full_name": "Maya Lin",
                "role": RoleChoices.STUDENT,
                "department": "Mechanical Engineering",
                "student_id": "2024-10088",
                "is_superuser": False,
                "is_staff": False
            }
        ]

        created_profiles = {}
        for acc in accounts:
            user, created = User.objects.get_or_create(
                username=acc["username"],
                defaults={
                    "email": acc["email"],
                    "is_superuser": acc["is_superuser"],
                    "is_staff": acc["is_staff"]
                }
            )
            user.set_password(acc["password"])
            user.email = acc["email"]
            user.save()

            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = acc["role"]
            profile.full_name = acc["full_name"]
            profile.department = acc["department"]
            profile.student_id = acc["student_id"]
            profile.is_active = True
            profile.save()

            created_profiles[acc["username"]] = profile
            status_text = "Created" if created else "Updated"
            self.stdout.write(f"  [{status_text}] {acc['full_name']} ({acc['role']}) -> {acc['email']}")

        # Seed sample appointments
        now = timezone.now()
        counselor_m = created_profiles["counselor1"]
        counselor_s = created_profiles["counselor2"]
        student_a = created_profiles["student1"]
        student_m = created_profiles["student2"]

        # Upcoming appointment tomorrow 10:00 AM
        tomorrow_10am = (now + datetime.timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        appt1, _ = Appointment.objects.get_or_create(
            student=student_a,
            counselor=counselor_m,
            scheduled_at=tomorrow_10am,
            defaults={
                "status": AppointmentStatusChoices.CONFIRMED,
                "concern_type": ConcernTypeChoices.ACADEMIC,
                "notes": "Discussing midterm workload management and study strategies."
            }
        )

        # Past completed appointment
        past_week = (now - datetime.timedelta(days=7)).replace(hour=14, minute=0, second=0, microsecond=0)
        appt2, _ = Appointment.objects.get_or_create(
            student=student_a,
            counselor=counselor_m,
            scheduled_at=past_week,
            defaults={
                "status": AppointmentStatusChoices.COMPLETED,
                "concern_type": ConcernTypeChoices.MENTAL_HEALTH,
                "notes": "Initial intake session for stress resilience."
            }
        )

        # Encrypted Case Note for completed appointment
        encrypted_note = encrypt_text("Student responded well to cognitive reframing. Recommended timeboxing techniques. Follow up in two weeks.")
        CaseNote.objects.get_or_create(
            appointment=appt2,
            counselor=counselor_m,
            defaults={
                "content": encrypted_note,
                "is_confidential": False
            }
        )

        # Pending appointment for student2
        next_week = (now + datetime.timedelta(days=3)).replace(hour=11, minute=0, second=0, microsecond=0)
        Appointment.objects.get_or_create(
            student=student_m,
            counselor=counselor_s,
            scheduled_at=next_week,
            defaults={
                "status": AppointmentStatusChoices.PENDING,
                "concern_type": ConcernTypeChoices.CAREER,
                "notes": "Internship interview anxiety."
            }
        )

        self.stdout.write(self.style.SUCCESS("Successfully seeded test database fixtures!"))

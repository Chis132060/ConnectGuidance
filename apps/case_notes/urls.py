"""
apps/case_notes/urls.py — URL routing for Case Notes feature.

Implements FLOWS §11-12: Case note editor with AES-256 encryption.
"""

from django.urls import path
from apps.case_notes.views import counselor_case_note_view

urlpatterns = [
    path('counselor/case-notes/<int:appointment_id>/', counselor_case_note_view, name='case_note'),
]

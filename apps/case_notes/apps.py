"""
apps/case_notes/apps.py — Case Notes application configuration.

Feature: Secure case note management with AES-256 encryption.
"""

from django.apps import AppConfig


class CaseNotesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.case_notes'
    verbose_name = 'Case Notes'
    verbose_name = 'Case Notes'

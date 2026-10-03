"""
apps/case_notes/forms.py — Case Note forms for GuidanceConnect.

Implements secure case note editor with confidentiality controls.
"""

from django import forms


class CaseNoteForm(forms.Form):
    """
    Case note editor form with AES-256 encryption and confidentiality flag.
    Content is encrypted at rest by the save_case_note service.
    """
    content = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 8,
            'placeholder': 'Enter clinical assessment, notes, and follow-up plan (encrypted at rest)...',
            'id': 'note-content'
        })
    )
    is_confidential = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox', 'id': 'note-confidential'})
    )

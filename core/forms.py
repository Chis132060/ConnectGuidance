from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Profile, Appointment, CaseNote, StudentMoodAlert
from .choices import ConcernTypeChoices, RoleChoices, AppointmentStatusChoices


class StudentRegistrationForm(forms.Form):
    full_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your full name',
            'autocomplete': 'name',
            'id': 'reg-full-name'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'student@university.edu',
            'autocomplete': 'email',
            'id': 'reg-email'
        })
    )
    student_id = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. 2024-10293',
            'id': 'reg-student-id'
        })
    )
    department = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. Computer Science',
            'id': 'reg-department'
        })
    )
    password = forms.CharField(
        min_length=8,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'At least 8 characters',
            'autocomplete': 'new-password',
            'id': 'reg-password'
        })
    )
    confirm_password = forms.CharField(
        min_length=8,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm your password',
            'autocomplete': 'new-password',
            'id': 'reg-confirm-password'
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('A user with this email address already exists.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm = cleaned_data.get('confirm_password')
        if password and confirm and password != confirm:
            self.add_error('confirm_password', 'Passwords do not match.')
        return cleaned_data


class StudentProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['full_name', 'student_id', 'department']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-input'}),
            'student_id': forms.TextInput(attrs={'class': 'form-input'}),
            'department': forms.TextInput(attrs={'class': 'form-input'}),
        }


class AppointmentBookingForm(forms.Form):
    counselor_id = forms.IntegerField(
        required=True,
        widget=forms.HiddenInput(attrs={'id': 'booking-counselor-id'})
    )
    scheduled_at = forms.DateTimeField(
        required=True,
        input_formats=['%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S'],
        widget=forms.HiddenInput(attrs={'id': 'booking-scheduled-at'})
    )
    concern_type = forms.ChoiceField(
        choices=ConcernTypeChoices.choices,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'booking-concern-type'})
    )
    notes = forms.CharField(
        max_length=2000,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 4,
            'placeholder': 'Briefly share what you would like to discuss (optional, max 2000 characters)...',
            'id': 'booking-notes'
        })
    )


class ReceptionistBookingForm(forms.Form):
    student_id = forms.IntegerField(
        required=True,
        widget=forms.HiddenInput(attrs={'id': 'rec-student-id'})
    )
    counselor_id = forms.IntegerField(
        required=True,
        widget=forms.HiddenInput(attrs={'id': 'rec-counselor-id'})
    )
    scheduled_at = forms.DateTimeField(
        required=True,
        input_formats=['%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S'],
        widget=forms.HiddenInput(attrs={'id': 'rec-scheduled-at'})
    )
    concern_type = forms.ChoiceField(
        choices=ConcernTypeChoices.choices,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'rec-concern-type'})
    )
    notes = forms.CharField(
        max_length=2000,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 3,
            'placeholder': 'Front desk booking intake notes...',
            'id': 'rec-notes'
        })
    )


class CaseNoteForm(forms.Form):
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


class MoodCheckInForm(forms.Form):
    MOOD_CHOICES = [
        ('good', 'Good - Feeling positive and energetic'),
        ('okay', 'Okay - Doing alright, maintaining baseline'),
        ('low', 'Low - Overwhelmed, stressed, or needing support'),
    ]
    mood = forms.ChoiceField(
        choices=MOOD_CHOICES,
        required=True,
        widget=forms.RadioSelect(attrs={'class': 'mood-radio'})
    )
    note = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 3,
            'placeholder': 'Optional thoughts or context (max 500 characters)...',
            'id': 'mood-note'
        })
    )

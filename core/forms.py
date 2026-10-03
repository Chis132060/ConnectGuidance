from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Profile, Appointment, StudentMoodAlert
from apps.common.choices import ConcernTypeChoices, RoleChoices, AppointmentStatusChoices


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

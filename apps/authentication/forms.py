from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


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

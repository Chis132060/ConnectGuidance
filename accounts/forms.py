from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from accounts.constants import FSUU_PROGRAM_CHOICES
from accounts.models import Profile


class StudentRegistrationForm(forms.Form):
    full_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Full Legal Name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'student@university.edu'})
    )
    student_id = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Student ID Number'})
    )
    department = forms.ChoiceField(
        choices=[('', 'Select your college')] + FSUU_PROGRAM_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-input'}),
    )
    password = forms.CharField(
        min_length=8,
        required=True,
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Password (min. 8 characters)'})
    )
    confirm_password = forms.CharField(
        min_length=8,
        required=True,
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Confirm Password'})
    )

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get('password')
        confirm = cleaned_data.get('confirm_password')
        if pw and confirm and pw != confirm:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data


class StudentProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['full_name', 'student_id', 'department']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-input'}),
            'student_id': forms.TextInput(attrs={'class': 'form-input'}),
            'department': forms.Select(
                choices=[('', 'Select your college (optional)')] + FSUU_PROGRAM_CHOICES,
                attrs={'class': 'form-input'},
            ),
        }

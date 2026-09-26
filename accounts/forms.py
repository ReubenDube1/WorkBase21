from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm, UserCreationForm,
)
from django.contrib.auth.models import User

from .models import TrackedJob, UserProfile


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Username', 'autofocus': True
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Password'
        })


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'you@example.com'})
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Choose a username'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Create a password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Confirm password'
        })
        self.fields['email'].widget.attrs.update({'class': 'form-control'})

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


MAX_TAGS = 30


def _parse_names(raw, max_len):
    """Splits comma-separated text into clean, de-duplicated names
    (case-insensitive), keeping the job seeker's own capitalisation."""
    seen = {}
    for part in (raw or '').split(','):
        name = ' '.join(part.split())[:max_len].strip()
        if name and name.lower() not in seen:
            seen[name.lower()] = name
    return list(seen.values())[:MAX_TAGS]


def _get_or_create_by_name(model, name):
    """Reuses an existing Skill/Qualification if one matches the name
    case-insensitively ('python' reuses 'Python'), so typed entries
    still line up with job requirements for matching."""
    existing = model.objects.filter(name__iexact=name).first()
    return existing or model.objects.create(name=name)


class ProfileForm(forms.ModelForm):
    qualifications_text = forms.CharField(
        required=False,
        label='Qualifications',
        help_text='Separate with commas, e.g. BSc Computer Science, Matric',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. BSc Computer Science, Matric',
            'id': 'id_qualifications_text',
        }),
    )
    skills_text = forms.CharField(
        required=False,
        label='Skills',
        help_text='Separate with commas, e.g. Python, Excel, Customer Service',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. Python, Excel, Customer Service',
            'id': 'id_skills_text',
        }),
    )

    field_order = [
        'location', 'qualification_level', 'qualifications_text',
        'experience_level', 'career_goal', 'skills_text', 'bio',
    ]

    class Meta:
        model = UserProfile
        fields = [
            'location', 'qualification_level', 'experience_level',
            'career_goal', 'bio',
        ]
        widgets = {
            'location': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. Johannesburg, Gauteng'
            }),
            'qualification_level': forms.Select(attrs={'class': 'form-control'}),
            'experience_level': forms.Select(attrs={'class': 'form-control'}),
            'career_goal': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': "e.g. 'Data Analyst'"
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
                'placeholder': 'A short summary about yourself (optional).'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['skills_text'].initial = ', '.join(
                self.instance.skills.values_list('name', flat=True)
            )
            self.fields['qualifications_text'].initial = ', '.join(
                self.instance.qualifications.values_list('name', flat=True)
            )

    def clean_skills_text(self):
        return _parse_names(self.cleaned_data.get('skills_text'), 80)

    def clean_qualifications_text(self):
        return _parse_names(self.cleaned_data.get('qualifications_text'), 150)

    def save(self, commit=True):
        from jobs.models import Skill
        from .models import Qualification

        profile = super().save(commit=commit)
        if commit:
            profile.skills.set([
                _get_or_create_by_name(Skill, n)
                for n in self.cleaned_data['skills_text']
            ])
            profile.qualifications.set([
                _get_or_create_by_name(Qualification, n)
                for n in self.cleaned_data['qualifications_text']
            ])
        return profile


class TrackedJobForm(forms.ModelForm):
    class Meta:
        model = TrackedJob
        fields = ['status', 'applied_at', 'reminder_date', 'notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'applied_at': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'reminder_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
                'placeholder': 'e.g. Sent CV via email, contact person, interview questions to prepare...'
            }),
        }
        help_texts = {
            'applied_at': "Filled in automatically the first time you mark it as applied — change it if needed.",
        }


class _StyledFieldsMixin:
    """Gives every field the site's form-control styling."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class StyledPasswordResetForm(_StyledFieldsMixin, PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({'placeholder': 'The email you signed up with', 'autofocus': True})


class StyledSetPasswordForm(_StyledFieldsMixin, SetPasswordForm):
    pass


class StyledPasswordChangeForm(_StyledFieldsMixin, PasswordChangeForm):
    pass


class DeleteAccountForm(forms.Form):
    password = forms.CharField(
        label="Enter your password to confirm",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'current-password'}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data['password']
        if not self.user.check_password(password):
            raise forms.ValidationError("That password isn't correct.")
        return password

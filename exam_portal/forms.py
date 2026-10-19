from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Student, Test, Question, Option, TestCase


class StudentRegistrationForm(forms.ModelForm):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Choose username'
    }))
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control', 'placeholder': 'name@example.com'
    }))
    first_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'First Name'
    }))
    last_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Last Name'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'Create strong password'
    }))
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'Confirm password'
    }))

    class Meta:
        model = Student
        fields = ['roll_number', 'phone', 'college', 'department']
        widgets = {
            'roll_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 2026CS101'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., +91 9876543210'}),
            'college': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'College / Institute Name'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Computer Science'}),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError("This username is already taken. Please pick another.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('password_confirm')
        if p1 and p2 and p1 != p2:
            self.add_error('password_confirm', "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name']
        )
        student = super().save(commit=False)
        student.user = user
        if commit:
            student.save()
        return student


class TestForm(forms.ModelForm):
    class Meta:
        model = Test
        fields = [
            'title', 'description', 'duration_minutes', 'total_marks', 'pass_marks',
            'negative_marking', 'negative_mark_value', 'randomize_questions',
            'allow_multiple_attempts', 'is_active'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Python Core & Algorithmic Challenge'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Test details, topics covered, instructions...'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'total_marks': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'pass_marks': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'negative_mark_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.05', 'min': 0}),
            'negative_marking': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'randomize_questions': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_multiple_attempts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = [
            'question_type', 'title', 'prompt', 'marks', 'negative_marks', 
            'difficulty', 'order', 'sample_input', 'sample_output', 'starter_code', 'time_limit_seconds'
        ]
        widgets = {
            'question_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_question_type'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Short summary or title'}),
            'prompt': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Enter full question statement, constraints, etc.'}),
            'marks': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'negative_marks': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.05', 'min': 0}),
            'difficulty': forms.Select(attrs={'class': 'form-select'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'sample_input': forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 3, 'placeholder': 'Sample input (optional for MCQ)'}),
            'sample_output': forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 3, 'placeholder': 'Expected output for sample input'}),
            'starter_code': forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 5}),
            'time_limit_seconds': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': 0.5}),
        }

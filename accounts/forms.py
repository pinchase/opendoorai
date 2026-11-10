from django import forms
from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils.text import capfirst

from profiles.models import Profile


class RegistrationForm(forms.Form):
    full_name = forms.CharField(max_length=120, label="Full name")
    email = forms.EmailField(max_length=254)
    password1 = forms.CharField(
        label="Password", widget=forms.PasswordInput, strip=False
    )
    password2 = forms.CharField(
        label="Confirm password", widget=forms.PasswordInput, strip=False
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        from django.contrib.auth import get_user_model

        if get_user_model().objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean_password1(self):
        password = self.cleaned_data["password1"]
        password_validation.validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") and cleaned.get("password2"):
            if cleaned["password1"] != cleaned["password2"]:
                self.add_error("password2", "The passwords do not match.")
        return cleaned


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={"autocomplete": "email"}))

    def clean(self):
        email = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if email and password:
            from django.contrib.auth import get_user_model

            user_model = get_user_model()
            user = user_model.objects.filter(email__iexact=email).first()
            self.user_cache = authenticate(
                self.request,
                username=user.get_username() if user else email,
                password=password,
            )
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data


class ProfileForm(forms.ModelForm):
    preferred_categories = forms.MultipleChoiceField(
        label="Preferred opportunity categories",
        choices=Profile.CATEGORY_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Profile
        fields = [
            "full_name",
            "education_level",
            "institution",
            "field_of_study",
            "graduation_year",
            "skills",
            "interests",
            "career_goals",
            "preferred_categories",
            "preferred_location",
            "experience_level",
            "cv",
        ]
        widgets = {
            "skills": forms.Textarea(attrs={"rows": 3, "placeholder": "Python, research, communication"}),
            "interests": forms.Textarea(attrs={"rows": 3}),
            "career_goals": forms.Textarea(attrs={"rows": 3}),
            "cv": forms.FileInput(attrs={"accept": ".pdf,.doc,.docx"}),
        }

    def clean_cv(self):
        upload = self.cleaned_data.get("cv")
        if upload:
            if upload.size > 5 * 1024 * 1024:
                raise ValidationError("The CV must be 5 MB or smaller.")
            if upload.name.rsplit(".", 1)[-1].lower() not in {"pdf", "doc", "docx"}:
                raise ValidationError("Upload a PDF or Word document.")
        return upload

    def clean_graduation_year(self):
        year = self.cleaned_data.get("graduation_year")
        if year and not 1900 <= year <= 2200:
            raise ValidationError("Enter a year between 1900 and 2200.")
        return year

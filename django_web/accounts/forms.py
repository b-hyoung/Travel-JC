from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Profile

PASSWORD_HELP = "Use letters and numbers, up to 10 characters."


def validate_password_rules(password: str, messages=None):
    messages = messages or {}
    if not password:
        raise forms.ValidationError(messages.get("pw_error_empty", "Password is required."))
    if len(password) > 10:
        raise forms.ValidationError(messages.get("pw_error_length", "Password must be 1-10 characters."))
    if not password.isalnum():
        raise forms.ValidationError(messages.get("pw_error_require_both", "Include letters and numbers."))
    if not any(ch.isalpha() for ch in password) or not any(ch.isdigit() for ch in password):
        raise forms.ValidationError(messages.get("pw_error_require_both", "Include letters and numbers."))


class SignUpForm(UserCreationForm):
    full_name = forms.CharField(max_length=150, required=True, label="Name")
    visa_expiry = forms.DateField(
        required=False,
        label="Visa expiry",
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Account will be removed after this date.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("full_name", "username", "password1", "password2", "visa_expiry")

    def clean_password1(self):
        password1 = self.cleaned_data.get("password1") or ""
        validate_password_rules(password1, self._messages)
        return password1

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if username and User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                self._messages.get(
                    "username_exists",
                    "A user with that username already exists.",
                )
            )
        return username

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1") or ""
        password2 = self.cleaned_data.get("password2") or ""
        validate_password_rules(password2, self._messages)
        if password1 != password2:
            raise forms.ValidationError(self._messages.get("pw_mismatch", "Passwords do not match."))
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["full_name"]
        if commit:
            user.save()
            Profile.objects.create(
                user=user,
                visa_expiry=self.cleaned_data.get("visa_expiry"),
            )
        return user

    def __init__(self, *args, messages=None, **kwargs):
        self._messages = messages or {}
        super().__init__(*args, **kwargs)
        field_settings = {
            "full_name": {"placeholder": "Name", "id": "full-name"},
            "username": {"placeholder": "Username", "id": "username"},
            "password1": {"placeholder": "Password (letters+numbers, ≤10)", "id": "password"},
            "password2": {"placeholder": "Confirm password", "id": "confirm-password"},
            "visa_expiry": {"id": "visa-expiry"},
        }

        for name, attrs in field_settings.items():
            if name in self.fields:
                self.fields[name].widget.attrs.update(attrs)
        required_msg = self._messages.get("error_required", "This field is required.")
        invalid_username_msg = self._messages.get("username_invalid", "Enter a valid username.")
        for name in ("full_name", "username", "password1", "password2"):
            if name in self.fields:
                self.fields[name].error_messages["required"] = required_msg
        if "username" in self.fields:
            self.fields["username"].error_messages["invalid"] = invalid_username_msg
        if "visa_expiry" in self.fields:
            self.fields["visa_expiry"].error_messages["invalid"] = self._messages.get(
                "error_invalid_date",
                "Enter a valid date.",
            )
        for name in ("password1", "password2"):
            if name in self.fields:
                self.fields[name].help_text = PASSWORD_HELP


class PasswordResetByNameForm(forms.Form):
    full_name = forms.CharField(max_length=150, label="Name")
    username = forms.CharField(max_length=150, label="Username")
    new_password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput,
        help_text=PASSWORD_HELP,
    )
    new_password2 = forms.CharField(
        label="Confirm new password",
        widget=forms.PasswordInput,
    )

    def __init__(self, *args, messages=None, **kwargs):
        self._messages = messages or {}
        super().__init__(*args, **kwargs)
        required_msg = self._messages.get("error_required", "This field is required.")
        for name in ("full_name", "username", "new_password1", "new_password2"):
            if name in self.fields:
                self.fields[name].error_messages["required"] = required_msg

    def clean_new_password1(self):
        pw = self.cleaned_data.get("new_password1") or ""
        validate_password_rules(pw, self._messages)
        return pw

    def clean(self):
        cleaned = super().clean()
        pw1 = cleaned.get("new_password1")
        pw2 = cleaned.get("new_password2")
        if pw1 and pw2 and pw1 != pw2:
            self.add_error(
                "new_password2",
                self._messages.get("pw_mismatch", "Passwords do not match."),
            )
        return cleaned

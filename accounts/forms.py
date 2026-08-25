from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)


class UserAccountForm(forms.ModelForm):
    """Shared form for creating and editing staff/admin accounts.

    Password fields are optional on edit (leave blank to keep the current
    password) and required on create; this is controlled by passing
    ``instance`` in from the view, exactly like ``ModelForm`` normally works.
    """

    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        help_text="Leave blank to keep the current password.",
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
    )

    is_admin = forms.BooleanField(
        required=False,
        label="Admin access",
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # New accounts must set a password; existing accounts may leave it.
        self.fields["password"].required = not self.instance.pk
        self.fields["confirm_password"].required = not self.instance.pk

        if self.instance.pk:
            self.fields["is_admin"].initial = self.instance.is_superuser
        else:
            # "is_active" isn't shown on the create form at all (there's
            # nothing to deactivate yet) - drop it so an absent checkbox
            # can't be mistaken for "deactivate this brand new account".
            del self.fields["is_active"]

    def clean_username(self):
        username = self.cleaned_data["username"].strip()

        if not username:
            raise ValidationError("Username is required.")

        return username

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password or confirm_password:

            if password != confirm_password:
                raise ValidationError("Passwords do not match.")

            try:
                validate_password(password)
            except ValidationError as exc:
                self.add_error("password", exc)

        return cleaned_data

    def save(self, commit=True):
        is_new = self.instance.pk is None

        user = super().save(commit=False)

        password = self.cleaned_data.get("password")

        if password:
            user.set_password(password)

        is_admin = self.cleaned_data.get("is_admin", False)
        user.is_superuser = is_admin
        user.is_staff = is_admin

        if is_new:
            user.is_active = True

        if commit:
            user.save()

        return user

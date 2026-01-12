from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
import secrets


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=20, blank=True)
    visa_expiry = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} profile"


class RememberedLogin(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="remembered_logins")
    token = models.CharField(max_length=128, unique=True)
    language = models.CharField(max_length=8, default="en")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    last_used = models.DateTimeField(default=timezone.now)
    active = models.BooleanField(default=True)

    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(32)

    def touch(self):
        self.last_used = timezone.now()
        self.save(update_fields=["last_used"])

    def __str__(self):
        return f"{self.user.username} remembered login"

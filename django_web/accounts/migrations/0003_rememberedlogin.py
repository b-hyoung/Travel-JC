from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_profile_visa_expiry"),
    ]

    operations = [
        migrations.CreateModel(
            name="RememberedLogin",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token", models.CharField(max_length=128, unique=True)),
                ("language", models.CharField(default="en", max_length=8)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("last_used", models.DateTimeField(default=django.utils.timezone.now)),
                ("active", models.BooleanField(default=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="remembered_logins",
                        to="auth.user",
                    ),
                ),
            ],
        ),
    ]

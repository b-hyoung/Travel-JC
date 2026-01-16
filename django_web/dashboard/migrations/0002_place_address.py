from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("dashboard", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="place",
            name="address",
            field=models.CharField(max_length=200, blank=True, default=""),
        ),
    ]

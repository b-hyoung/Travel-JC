import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from dashboard.models import Place, QRVisit


class Command(BaseCommand):
    help = "Seed demo places and QR visit data."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=120)
        parser.add_argument("--users", type=int, default=4)
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **options):
        random.seed(options["seed"])
        count = options["count"]
        user_count = options["users"]

        places = [
            ("JHM", "전주한옥마을"),
            ("GGJ", "경기전"),
            ("JDC", "전동성당"),
            ("NBM", "남부시장/청년몰"),
            ("GDL", "객리단길"),
            ("ZMW", "자만벽화마을"),
            ("DJP", "덕진공원"),
        ]
        place_objs = []
        for code, name in places:
            place, _ = Place.objects.get_or_create(code=code, defaults={"name": name})
            place_objs.append(place)

        User = get_user_model()
        users = []
        for i in range(user_count):
            username = f"demo{i + 1}"
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password("demo1234")
                user.save(update_fields=["password"])
            users.append(user)

        now = timezone.now()
        visits = []
        for i in range(count):
            to_place = random.choice(place_objs)
            from_place = random.choice(place_objs)
            if from_place == to_place:
                from_place = None
            user = random.choice(users)
            created_at = now - timedelta(days=random.randint(0, 14), hours=random.randint(0, 23))
            visits.append(
                QRVisit(
                    user=user,
                    from_place=from_place,
                    to_place=to_place,
                    created_at=created_at,
                )
            )

        QRVisit.objects.bulk_create(visits)
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(place_objs)} places and {len(visits)} visits."))

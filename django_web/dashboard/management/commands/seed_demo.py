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
            ("JJS", "전주역", "전북특별자치도 전주시 덕진구 동부대로 680"),
            ("JBT", "전주고속버스터미널", "전북특별자치도 전주시 덕진구 가리내로 70"),
            ("JHM", "전주한옥마을", "전북특별자치도 전주시 완산구 풍남동3가 63-1"),
            ("JDC", "전동성당", "전북특별자치도 전주시 완산구 태조로 51"),
            ("GGJ", "경기전", "전북특별자치도 전주시 완산구 태조로 44"),
            ("OMD", "오목대", "전북특별자치도 전주시 완산구 기린대로 55"),
            ("NBM", "전주 남부시장", "전북특별자치도 전주시 완산구 풍남문2길 49"),
            ("ZMW", "자만벽화마을", "전북특별자치도 전주시 완산구 교동 50-79"),
            ("JZO", "전주 동물원", "전북특별자치도 전주시 덕진구 소리로 68"),
            ("DJP", "덕진공원", "전북특별자치도 전주시 덕진구 권삼득로 390"),
            ("AJH", "아중호수", "전북특별자치도 전주시 덕진구 우아동1가 786"),
        ]
        place_objs = []
        for code, name, address in places:
            place, _ = Place.objects.get_or_create(
                code=code,
                defaults={"name": name, "address": address},
            )
            updates = {}
            if place.name != name:
                updates["name"] = name
            if place.address != address:
                updates["address"] = address
            if updates:
                for key, value in updates.items():
                    setattr(place, key, value)
                place.save(update_fields=sorted(updates.keys()))
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

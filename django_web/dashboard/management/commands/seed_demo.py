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
            ("JJS", "전주역", "전주, 680, 동부대로, 우아동3가, 덕진구, 전주시, 전북특별자치도, 54908, 대한민국"),
            ("JHM", "전주한옥마을", "전주한옥마을 실내공영주차장, 어진길, 풍남동2가, 완산구, 전주시, 전북특별자치도, 55042, 대한민국"),
            ("JDC", "전동성당", "전동성당, 전동성당길, 전동, 완산구, 전주시, 전북특별자치도, 55039, 대한민국"),
            ("GGJ", "경기전", "전주 경기전, 전동성당길, 경원동2가, 완산구, 전주시, 전북특별자치도, 55039, 대한민국"),
            ("OMD", "오목대", "오목대, 전주시, 전북특별자치도, 55041, 대한민국"),
            ("NBM", "전주 남부시장", "전북특별자치도 전주시 완산구 풍남문1길 19-3"),
            ("ZMW", "자만벽화마을", "자만벽화마을, 자만동2길, 교동, 완산구, 전주시, 전북특별자치도, 55041, 대한민국"),
            ("JZO", "전주 동물원", "전주동물원, 소리로, 뜨란채 아파트 1,2차, 덕진구, 전주시, 전북특별자치도, 54902, 대한민국"),
            ("DJP", "덕진공원", "덕진공원, 덕진구, 전주시, 전북특별자치도, 54846, 대한민국"),
            ("AJH", "아중호수", "아중호수, 덕진구, 전주시, 전북특별자치도, 대한민국"),
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

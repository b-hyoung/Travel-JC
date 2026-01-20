from django.core.management.base import BaseCommand

from dashboard.models import Place


PLACES = [
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


class Command(BaseCommand):
    help = "Upsert place names and addresses."

    def handle(self, *args, **options):
        updated = 0
        created = 0
        for code, name, address in PLACES:
            place, was_created = Place.objects.get_or_create(
                code=code, defaults={"name": name, "address": address}
            )
            if was_created:
                created += 1
                continue
            fields = {}
            if place.name != name:
                fields["name"] = name
            if place.address != address:
                fields["address"] = address
            if fields:
                for key, value in fields.items():
                    setattr(place, key, value)
                place.save(update_fields=sorted(fields.keys()))
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Places synced. created={created}, updated={updated}"
            )
        )

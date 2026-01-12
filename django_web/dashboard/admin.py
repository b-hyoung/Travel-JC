from django.contrib import admin

from .models import Place, QRVisit


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")


@admin.register(QRVisit)
class QRVisitAdmin(admin.ModelAdmin):
    list_display = ("to_place", "from_place", "user", "created_at")
    list_filter = ("to_place", "from_place", "created_at")
    search_fields = ("to_place__name", "from_place__name", "user__username")

# Register your models here.

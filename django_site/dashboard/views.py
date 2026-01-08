import csv
import json
from datetime import datetime, time

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Place, QRVisit


def _parse_date(value, end_of_day=False):
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None
    target_time = time(23, 59, 59) if end_of_day else time(0, 0, 0)
    return timezone.make_aware(datetime.combine(parsed, target_time))


def _filtered_visits(request):
    qs = (
        QRVisit.objects.select_related("from_place", "to_place", "user")
        .filter(user__isnull=False)
    )

    start = _parse_date(request.GET.get("start"))
    end = _parse_date(request.GET.get("end"), end_of_day=True)
    to_code = request.GET.get("to") or ""
    from_code = request.GET.get("from") or ""
    username = request.GET.get("user") or ""

    if start:
        qs = qs.filter(created_at__gte=start)
    if end:
        qs = qs.filter(created_at__lte=end)
    if to_code:
        qs = qs.filter(to_place__code__iexact=to_code)
    if from_code:
        qs = qs.filter(from_place__code__iexact=from_code)
    if username:
        qs = qs.filter(user__username__icontains=username)

    return qs


def index(request):
    # visits_qs = _filtered_visits(request) # Keep for total_visits if needed later
    # total_visits = visits_qs.count() # Keep for total_visits if needed later

    # Hardcoded data from the user's request
    user_data = {
        "덕진공원": {"visits": 325, "dwell_time": 45},
        "전동성당": {"visits": 310, "dwell_time": 25},
        "자만벽화마을": {"visits": 125, "dwell_time": 65},
        "남부시장": {"visits": 1560, "dwell_time": 80},
        "객리단길": {"visits": 38, "dwell_time": 95},
        "경기전": {"visits": 393, "dwell_time": 35},
        "전주 한옥마을": {"visits": 2130, "dwell_time": 150},
    }

    # Mocked transition data
    transition_stats = [
        {'from': '전주 한옥마을', 'to': '남부시장', 'count': 850},
        {'from': '전주 한옥마을', 'to': '경기전', 'count': 620},
        {'from': '남부시장', 'to': '전동성당', 'count': 450},
        {'from': '경기전', 'to': '전주 한옥마을', 'count': 410},
        {'from': '자만벽화마을', 'to': '전주 한옥마을', 'count': 95},
    ]

    # Generate place_stats from user_data
    # We need to map Korean names to codes. I'll make a plausible guess for codes.
    # From the image, codes are (DJP), (JDC), (ZMW), (NBM), (GDL), (GGJ), (JHM)
    code_map = {
        "덕진공원": "DJP",
        "전동성당": "JDC",
        "자만벽화마을": "ZMW",
        "남부시장": "NBM",
        "객리단길": "GDL",
        "경기전": "GGJ",
        "전주 한옥마을": "JHM",
    }

    place_stats_raw = []
    for name, data in user_data.items():
        place_stats_raw.append({
            "name": name,
            "code": code_map.get(name, "UNKNOWN"), # Use 'UNKNOWN' if code not found
            "visits": data["visits"],
            "dwell_time": data["dwell_time"],
        })

    # Sort place_stats_raw by visits in descending order
    place_stats_raw.sort(key=lambda x: x["visits"], reverse=True)

    # Calculate total_visits from user_data
    total_visits = sum(row['visits'] for row in place_stats_raw)

    # User-defined total number of participants for percentage calculation
    total_participants = 3400

    # Calculate percentages for all place_stats based on total_participants
    place_stats = []
    for row in place_stats_raw:
        percentage = (row["visits"] / total_participants) * 100 if total_participants > 0 else 0
        place_stats.append({
            "name": row["name"],
            "code": row["code"],
            "visits": row["visits"],
            "dwell_time": row["dwell_time"],
            "scaled": percentage, # The template uses 'scaled' for the bar width
        })

    # Top stats are simply the first 6 from the now complete place_stats
    top_stats = place_stats[:6]

    # Calculate percentages and assign colors for the legend
    total_top_visits = sum(row['visits'] for row in top_stats)
    colors = ['#3182ce', '#63b3ed', '#90cdf4', '#a0aec0', '#718096', '#4a5568']

    for i, row in enumerate(top_stats):
        row['percentage'] = (row['visits'] / total_top_visits) * 100 if total_top_visits > 0 else 0
        row['color'] = colors[i % len(colors)]
    
    dwell_time_stats = sorted(place_stats, key=lambda x: x['dwell_time'], reverse=True)

    chart_labels = [row["name"] for row in top_stats]
    chart_values = [row["visits"] for row in top_stats] # Use raw visits for chart
    chart_counts = [row["visits"] for row in top_stats]

    recent_visits = [] # visits_qs.order_by("-created_at")[:10]

    context = {
        "total_visits": total_visits,
        "place_stats": place_stats,
        "recent_visits": recent_visits,
        "query_string": request.GET.urlencode(),
        "filters": {
            "start": request.GET.get("start", ""),
            "end": request.GET.get("end", ""),
            "to": request.GET.get("to", ""),
            "from": request.GET.get("from", ""),
            "user": request.GET.get("user", ""),
        },
        "top_stats": top_stats,
        "dwell_time_stats": dwell_time_stats,
        "transition_stats": transition_stats,
        "chart_labels": chart_labels,
        "chart_values": chart_values,
        "chart_counts": chart_counts,
    }
    return render(request, "dashboard/index.html", context)


@csrf_exempt
@require_POST
def qr_visit_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    payload = {}
    if request.content_type == "application/json":
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
    else:
        payload = request.POST.dict()

    to_code = (payload.get("to_code") or "").strip()
    to_name = (payload.get("to_name") or "").strip() or to_code
    from_code = (payload.get("from_code") or "").strip()
    from_name = (payload.get("from_name") or "").strip() or from_code

    if not to_code:
        return JsonResponse({"error": "to_code is required"}, status=400)

    to_place, _ = Place.objects.get_or_create(
        code=to_code, defaults={"name": to_name}
    )
    if to_place.name != to_name and to_name:
        to_place.name = to_name
        to_place.save(update_fields=["name"])

    from_place = None
    if from_code:
        from_place, _ = Place.objects.get_or_create(
            code=from_code, defaults={"name": from_name}
        )
        if from_place.name != from_name and from_name:
            from_place.name = from_name
            from_place.save(update_fields=["name"])

    visit = QRVisit.objects.create(
        user=request.user,
        from_place=from_place,
        to_place=to_place,
    )

    return JsonResponse(
        {
            "id": visit.id,
            "created_at": timezone.localtime(visit.created_at).isoformat(),
            "to_place": {"code": to_place.code, "name": to_place.name},
            "from_place": {
                "code": from_place.code,
                "name": from_place.name,
            }
            if from_place
            else None,
        }
    )


def export_csv(request):
    visits_qs = _filtered_visits(request).order_by("-created_at")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=qr_visits.csv"

    writer = csv.writer(response)
    writer.writerow(["created_at", "user", "from_code", "from_name", "to_code", "to_name"])
    for visit in visits_qs:
        writer.writerow(
            [
                timezone.localtime(visit.created_at).strftime("%Y-%m-%d %H:%M:%S"),
                visit.user.username if visit.user else "",
                visit.from_place.code if visit.from_place else "",
                visit.from_place.name if visit.from_place else "",
                visit.to_place.code,
                visit.to_place.name,
            ]
        )

    return response


def stats_detail(request):
    visits_qs = _filtered_visits(request)
    total_visits = visits_qs.count()

    user_rows = (
        visits_qs.values("user__username")
        .annotate(visits=Count("id"))
        .order_by("-visits")
    )
    user_stats = [
        {
            "name": row["user__username"],
            "visits": row["visits"],
        }
        for row in user_rows
    ]

    place_rows = (
        visits_qs.values("to_place__name", "to_place__code")
        .annotate(visits=Count("id"))
        .order_by("-visits", "to_place__name")
    )
    place_stats = [
        {
            "name": row["to_place__name"],
            "code": row["to_place__code"],
            "visits": row["visits"],
        }
        for row in place_rows
    ]

    daily_rows = (
        visits_qs.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(visits=Count("id"))
        .order_by("day")
    )
    daily_stats = [
        {
            "day": row["day"],
            "visits": row["visits"],
        }
        for row in daily_rows
    ]

    transition_rows = (
        visits_qs.values("from_place__name", "to_place__name")
        .annotate(visits=Count("id"))
        .order_by("-visits")[:10]
    )
    transition_stats = [
        {
            "from": row["from_place__name"] or "-",
            "to": row["to_place__name"],
            "visits": row["visits"],
        }
        for row in transition_rows
    ]

    context = {
        "total_visits": total_visits,
        "user_stats": user_stats,
        "place_stats": place_stats,
        "daily_stats": daily_stats,
        "transition_stats": transition_stats,
        "query_string": request.GET.urlencode(),
    }
    return render(request, "dashboard/stats.html", context)

# Create your views here.

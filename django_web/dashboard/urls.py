from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="dashboard-index"),
    path("stats/", views.stats_detail, name="dashboard-stats"),
    path("api/qr-visit/", views.qr_visit_api, name="dashboard-qr-visit"),
    path("export/csv/", views.export_csv, name="dashboard-export-csv"),
]

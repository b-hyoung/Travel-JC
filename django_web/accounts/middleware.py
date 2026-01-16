from django.shortcuts import redirect
from django.urls import reverse

from .i18n import normalize_lang_code, translations


class LanguageQueryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path.startswith("/static/") or path.startswith("/admin/"):
            return self.get_response(request)

        language_select_path = reverse("language_select")
        if path == language_select_path:
            return self.get_response(request)

        lang = normalize_lang_code(request.GET.get("lang"))
        if lang and lang in translations:
            request.session["lang"] = lang

        if request.session.get("lang") not in translations:
            return redirect("language_select")

        return self.get_response(request)

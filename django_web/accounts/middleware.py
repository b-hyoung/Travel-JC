from urllib.parse import urlencode

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
        lang_param = normalize_lang_code(request.GET.get("lang"))
        session_lang = normalize_lang_code(request.session.get("lang"))
        cookie_lang = normalize_lang_code(request.COOKIES.get("lang"))

        lang = None
        if lang_param in translations:
            lang = lang_param
        elif session_lang in translations:
            lang = session_lang
        elif cookie_lang in translations:
            lang = cookie_lang

        if lang:
            request.session["lang"] = lang
            response = self.get_response(request)
            if request.COOKIES.get("lang") != lang:
                response.set_cookie("lang", lang, max_age=60 * 60 * 24 * 365, samesite="Lax")
            return response

        if path == language_select_path:
            return self.get_response(request)

        next_path = request.get_full_path()
        query = urlencode({"next": next_path})
        return redirect(f"{language_select_path}?{query}")

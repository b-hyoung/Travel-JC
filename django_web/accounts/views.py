from datetime import date

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import PasswordResetByNameForm, SignUpForm
from .i18n import get_translation, normalize_lang_code, translations
from .models import Profile, RememberedLogin
from dashboard.models import Place, QRVisit

AUTOLOGIN_COOKIE = "auto_login_token"
AUTOLOGIN_MAX_AGE = 60 * 60 * 24 * 90  # 90 days


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _get_lang(request):
    lang = normalize_lang_code(request.GET.get("lang") or request.session.get("lang"))
    if lang and lang in translations:
        request.session["lang"] = lang
        return lang
    return None


def _attempt_auto_login(request):
    if request.user.is_authenticated:
        return None
    token = request.COOKIES.get(AUTOLOGIN_COOKIE)
    if not token:
        return None
    try:
        saved = RememberedLogin.objects.select_related("user").get(token=token, active=True)
    except RememberedLogin.DoesNotExist:
        return None
    user = saved.user
    user.backend = "django.contrib.auth.backends.ModelBackend"
    login(request, user)
    _set_session_expiry(request, True)
    request.session["lang"] = normalize_lang_code(saved.language) or "en"
    saved.last_used = timezone.now()
    saved.save(update_fields=["last_used"])
    return user


def _set_auto_login(request, user, lang, response):
    RememberedLogin.objects.filter(user=user, active=True).delete()
    token = RememberedLogin.generate_token()
    RememberedLogin.objects.create(
        user=user,
        token=token,
        language=lang or "en",
        ip_address=_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
    )
    response.set_cookie(
        AUTOLOGIN_COOKIE,
        token,
        max_age=AUTOLOGIN_MAX_AGE,
        httponly=True,
        samesite="Lax",
    )


def _clear_auto_login(request, response):
    token = request.COOKIES.get(AUTOLOGIN_COOKIE)
    if token:
        RememberedLogin.objects.filter(token=token).update(active=False)
        response.delete_cookie(AUTOLOGIN_COOKIE)


def _set_session_expiry(request, remember_me):
    request.session["remember_me"] = bool(remember_me)
    if remember_me:
        request.session.set_expiry(AUTOLOGIN_MAX_AGE)
    else:
        request.session.set_expiry(0)


def _get_remembered_language(request):
    token = request.COOKIES.get(AUTOLOGIN_COOKIE)
    if not token:
        return None
    saved = RememberedLogin.objects.filter(token=token, active=True).first()
    if saved:
        lang = normalize_lang_code(saved.language)
        if lang in translations:
            return lang
    return None


def _update_auto_login_language(request, lang):
    token = request.COOKIES.get(AUTOLOGIN_COOKIE)
    if not token:
        return
    RememberedLogin.objects.filter(token=token, active=True).update(
        language=lang,
        last_used=timezone.now(),
    )


def language_select(request):
    manual = request.GET.get("manual") == "1"
    if not manual and _attempt_auto_login(request):
        return redirect("dashboard")
    if request.user.is_authenticated and not manual:
        lang = request.session.get("lang")
        if not lang or lang not in translations:
            request.session["lang"] = _get_remembered_language(request) or "en"
        return redirect("dashboard")
    lang_param = normalize_lang_code(request.GET.get("lang"))
    if lang_param:
        selected_lang = lang_param if lang_param in translations else "en"
        request.session["lang"] = selected_lang
        _update_auto_login_language(request, selected_lang)
        return redirect("login")
    lang = request.session.get("lang") or "en"
    t = get_translation(lang)
    language_list = [{"code": code, "name": data["language_name"]} for code, data in translations.items()]
    return render(
        request,
        "accounts/language_select.html",
        {"languages": language_list, "t": t, "lang": lang},
    )


def signup_view(request):
    auto_user = _attempt_auto_login(request)
    if auto_user:
        return redirect("dashboard")
    lang = _get_lang(request)
    if not lang:
        return redirect("language_select")
    t = get_translation(lang)
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = SignUpForm(request.POST, messages=t)
        if form.is_valid():
            form.save()
            request.session["lang"] = lang
            messages.success(request, t["signup_success"])
            return redirect("login")
        
    else:
        form = SignUpForm(messages=t)

    # localize labels/placeholders/help
    form.fields["full_name"].label = t["name_label"]
    form.fields["username"].label = t["username_label"]
    form.fields["password1"].label = t["password_label"]
    form.fields["password2"].label = t["password_confirm_label"]
    form.fields["visa_expiry"].label = t["visa_label"]
    placeholders = {
        "full_name": t["name_label"],
        "username": t["username_label"],
        "password1": t["password_label"],
        "password2": t["password_confirm_label"],
    }
    for name, value in placeholders.items():
        if name in form.fields:
            form.fields[name].widget.attrs["placeholder"] = value

    form.fields["password1"].help_text = t["password_hint_length"]
    form.fields["password2"].help_text = ""

    return render(
        request,
        "accounts/signup.html",
        {"form": form, "t": t, "lang": lang},
    )


def login_view(request):
    auto_user = _attempt_auto_login(request)
    if auto_user:
        return redirect("dashboard")
    lang = _get_lang(request)
    if not lang:
        return redirect("language_select")
    t = get_translation(lang)
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = AuthenticationForm(request, data=request.POST or None)
    form.fields["username"].widget.attrs.update({"placeholder": t["username_label"]})
    form.fields["password"].widget.attrs.update({"placeholder": t["password_label"]})
    form.fields["username"].label = t["username_label"]
    form.fields["password"].label = t["password_label"]
    required_msg = t.get("error_required", "This field is required.")
    invalid_username_msg = t.get("username_invalid", "Enter a valid username.")
    form.fields["username"].error_messages["required"] = required_msg
    form.fields["username"].error_messages["invalid"] = invalid_username_msg
    form.fields["password"].error_messages["required"] = required_msg
    form.error_messages["invalid_login"] = t.get(
        "login_error_invalid",
        "Invalid username or password.",
    )
    form.error_messages["inactive"] = t.get(
        "login_error_inactive",
        "This account is inactive.",
    )

    if request.method == "POST":
        if form.is_valid():
            user = form.get_user()
            profile = getattr(user, "profile", None)
            if profile and profile.visa_expiry and profile.visa_expiry < date.today():
                username = user.username
                user.delete()
                messages.error(request, t["visa_notice"])
                return redirect("signup")
            login(request, user)
            request.session["lang"] = lang
            resp = redirect("dashboard")
            remember_me = bool(request.POST.get("remember_me"))
            _set_session_expiry(request, remember_me)
            if remember_me:
                _set_auto_login(request, user, lang, resp)
            else:
                _clear_auto_login(request, resp)
            messages.success(request, t["login_success"])
            return resp
        

    return render(request, "accounts/login.html", {"form": form, "t": t, "lang": lang})


def logout_view(request):
    resp = redirect("login")
    _clear_auto_login(request, resp)
    logout(request)
    return resp


@login_required
def dashboard_view(request):
    profile = getattr(request.user, "profile", None)
    lang = _get_lang(request)
    if not lang:
        return redirect("language_select")
    t = get_translation(lang)

    # Get all places from the database
    all_places = Place.objects.all()

    # Get all visits for the current user
    user_visits = QRVisit.objects.filter(user=request.user)
    
    # Create a set of visited place IDs for quick lookups
    visited_place_ids = set(user_visits.values_list('to_place_id', flat=True))

    # Create the list of spots with dynamic 'scanned' status
    qr_spots = []
    start_place_codes = {"JJS", "JBT"}
    for place in all_places:
        qr_spots.append({
            "name": place.name,
            "scanned": place.id in visited_place_ids,
            "label": (
                t.get("dashboard_start_label", t["dashboard_spot_label"])
                if place.code in start_place_codes
                else t["dashboard_spot_label"]
            ),
            "address": place.address,
        })

    # Calculate progress. The template uses tour_spots for progress calculation.
    # We will use all qr_spots for this calculation.
    scanned_count = sum(1 for spot in qr_spots if spot["scanned"])
    total_count = len(qr_spots)
    progress_percent = int(round((scanned_count / total_count) * 100)) if total_count else 0

    recommended_routes = [
        {
            "title": "A코스 (핵심 도보투어)",
            "progress": 35,
            "stops": ["전주역", "전주한옥마을", "전동성당", "경기전", "오목대"],
            "summary": "전주한옥마을, 전동성당, 경기전, 오목대 등을 둘러보는 코스입니다.",
        },
        {
            "title": "B코스 (야시장 & 벽화투어)",
            "progress": 25,
            "stops": ["전주역", "전주 남부시장", "전주한옥마을", "자만벽화마을"],
            "summary": "전주 남부시장, 전주한옥마을, 자만벽화마을 등을 둘러보는 코스입니다.",
        },
        {
            "title": "C코스 (공원 & 자연투어)",
            "progress": 22,
            "stops": ["전주역", "전주 동물원", "덕진공원", "아중호수"],
            "summary": "전주 동물원, 덕진공원, 아중호수 등을 둘러보는 코스입니다.",
        },
        {
            "title": "D코스 (전통 문화탐방)",
            "progress": 10,
            "stops": ["전주역", "경기전", "전동성당", "전주 남부시장"],
            "summary": "경기전, 전동성당, 전주 남부시장 등을 둘러보는 코스입니다.",
        },
        {
            "title": "E코스 (느린 산책투어)",
            "progress": 8,
            "stops": ["전주역", "전주한옥마을", "자만벽화마을", "오목대"],
            "summary": "전주한옥마을, 자만벽화마을, 오목대 등을 둘러보는 코스입니다.",
        },
    ]
    for route in recommended_routes:
        route["path"] = " -> ".join(route["stops"])
    
    return render(
        request,
        "accounts/dashboard.html",
        {
            "profile": profile,
            "t": t,
            "lang": lang,
            "qr_spots": qr_spots,
            "tour_spots": qr_spots, # Using qr_spots for map view as well
            "kiosk_spots": [], # Kiosk spots are not in DB, so empty list
            "recommended_routes": recommended_routes,
            "scanned_count": scanned_count,
            "total_count": total_count,
            "progress_percent": progress_percent,
        },
    )


def password_reset_by_name(request):
    auto_user = _attempt_auto_login(request)
    if auto_user:
        return redirect("dashboard")
    lang = _get_lang(request)
    if not lang:
        return redirect("language_select")
    t = get_translation(lang)
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = PasswordResetByNameForm(request.POST or None, messages=t)
    if request.method == "POST" and form.is_valid():
        User = get_user_model()
        try:
            user = User.objects.get(username=form.cleaned_data["username"])
        except User.DoesNotExist:
            messages.error(request, t["password_reset_user_not_found"])
        else:
            if user.first_name != form.cleaned_data["full_name"]:
                messages.error(request, t["password_reset_name_mismatch"])
            else:
                user.set_password(form.cleaned_data["new_password1"])
                user.save()
                messages.success(request, t["pw_match"])
                return redirect("login")

    # localize labels
    form.fields["full_name"].label = t["name_label"]
    form.fields["username"].label = t["username_label"]
    form.fields["new_password1"].label = t["password_label"]
    form.fields["new_password2"].label = t["password_confirm_label"]

    return render(
        request,
        "accounts/password_reset_by_name.html",
        {"form": form, "t": t, "lang": lang},
    )

# Create your views here.

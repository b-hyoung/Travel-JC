from datetime import date

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import PasswordResetByNameForm, SignUpForm
from .i18n import get_translation, translations
from .models import Profile, RememberedLogin

AUTOLOGIN_COOKIE = "auto_login_token"
AUTOLOGIN_MAX_AGE = 60 * 60 * 24 * 90  # 90 days


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _get_lang(request):
    lang = request.GET.get("lang") or request.session.get("lang")
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
    request.session["lang"] = saved.language or "en"
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
    if saved and saved.language in translations:
        return saved.language
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
    lang_param = request.GET.get("lang")
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
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            request.session["lang"] = lang
            resp = redirect("dashboard")
            remember_me = bool(request.POST.get("remember_me"))
            _set_session_expiry(request, remember_me)
            if remember_me:
                _set_auto_login(request, user, lang, resp)
            else:
                _clear_auto_login(request, resp)
            messages.success(request, t["signup_button"] + " 완료")
            return resp
        messages.error(request, t["pw_error_length"])
    else:
        form = SignUpForm()

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
            messages.success(request, t["login_button"] + " 완료")
            return resp
        messages.error(request, t["pw_error_require_both"])

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
    return render(
        request,
        "accounts/dashboard.html",
        {"profile": profile, "t": t, "lang": lang},
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

    form = PasswordResetByNameForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        User = get_user_model()
        try:
            user = User.objects.get(username=form.cleaned_data["username"])
        except User.DoesNotExist:
            messages.error(request, "해당 아이디를 찾을 수 없습니다.")
        else:
            if user.first_name != form.cleaned_data["full_name"]:
                messages.error(request, t["name_label"] + "이 일치하지 않습니다.")
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

import os, re, dj_database_url
from pathlib import Path
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
DEBUG = os.getenv("DEBUG", "True") == "True"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
APPLE_CLIENT_ID = os.getenv("APPLE_CLIENT_ID", "")
INSTALLED_APPS = ["django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "rest_framework", "rest_framework.authtoken", "corsheaders", "store"]
MIDDLEWARE = ["corsheaders.middleware.CorsMiddleware", "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware", "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware"]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [], "APP_DIRS": True,
    "OPTIONS": {"context_processors": ["django.template.context_processors.request",
    "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default": dj_database_url.config(default=f"sqlite:///{BASE_DIR/'db.sqlite3'}")}
STATIC_URL = "/static/"; STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"; MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
_front = os.getenv("FRONTEND_URL", "http://localhost:5173").strip().rstrip("/")
CORS_ALLOWED_ORIGINS = sorted({o.strip().rstrip("/") for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()} | {_front})
CSRF_TRUSTED_ORIGINS = [o for o in CORS_ALLOWED_ORIGINS if o.startswith("http")] + [o.strip() for o in os.getenv("CSRF_ORIGINS", "").split(",") if o.strip()]
REST_FRAMEWORK = {"DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication", "rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"]}

# Chennai store (shown on website maps + admin tracking map). Edit lat/lng to your exact shop.
STORE = {"name": "StepUp.in Store", "address": "No. 14, Anna Salai, Teynampet, Chennai, Tamil Nadu 600018",
         "lat": 13.0418, "lng": 80.2500, "phone": "+91 98412 36547"}

# ---- Email / SMTP (used for sign-up verification codes) ----
_clean = lambda v: re.sub(r"[^\x21-\x7e]", "", v or "").strip("'\"")   # drops spaces, non-breaking spaces, hidden characters, quotes
_u = _clean(os.getenv("EMAIL_HOST_USER")); _p = _clean(os.getenv("EMAIL_HOST_PASSWORD"))
_fake = (not _u) or _u.lower() in ("skip", "none", "-") or "yourname" in _u or "your-16" in _p or not _p     # placeholder values => use console mode
EMAIL_HOST_USER = "" if _fake else _u; EMAIL_HOST_PASSWORD = "" if _fake else _p
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend" if EMAIL_HOST_USER else "django.core.mail.backends.console.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com"); EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587")); EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "").strip() or EMAIL_HOST_USER or "no-reply@stepup.in"
EMAIL_TIMEOUT = 20
FIRST_ORDER = {"percent": 50, "cap": 1500, "gift": "StepUp shoe-care kit"}
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")  # used for product thumbnails in admin
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"  # OpenStreetMap blocks map tiles when no Referer is sent
SHOW_OTP_ON_SCREEN = os.getenv("SHOW_OTP_ON_SCREEN", "True") == "True"   # show the 6-digit code on the login page (demo). Set False for a live shop that emails codes
if not DEBUG:  # behind Render / Railway / Heroku style HTTPS proxies
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https"); USE_X_FORWARDED_HOST = True
    SESSION_COOKIE_SECURE = True; CSRF_COOKIE_SECURE = True
    SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin-allow-popups"

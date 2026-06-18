import os
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
env_file = os.path.join(BASE_DIR, ".env")

if not os.path.exists(env_file):
    env_file = os.path.join(BASE_DIR, ".env.example")

environ.Env.read_env(env_file)

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "testserver"])

INSTALLED_APPS = [
    "apps.accounts",
    "apps.estructura",
    "apps.actividades",
    "apps.planificacion",
    "apps.proyectos",
    "apps.gestion",
    "apps.dashboard",
    "apps.reportes",
    "apps.auditoria",
    "apps.core",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.auditoria.middleware.AuditLogMiddleware",
    "apps.accounts.middleware.RoleSwitchMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.proyectos.context_processors.proyecto_contexto",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

db_engine = env("DB_ENGINE", default="django.db.backends.sqlite3")
db_name = env("DB_NAME", default="db.sqlite3")

if db_engine in ["mssql", "sql_server"]:
    db_engine = "mssql"

DATABASES = {
    "default": {
        "ENGINE": db_engine,
        "NAME": (BASE_DIR / db_name) if db_engine == "django.db.backends.sqlite3" else db_name,
    }
}

if db_engine == "mssql":
    DATABASES["default"].update(
        {
            "HOST": env("DB_HOST", default=""),
            "PORT": env("DB_PORT", default=""),
            "USER": env("DB_USER", default=""),
            "PASSWORD": env("DB_PASSWORD", default=""),
            "OPTIONS": {
                "driver": env("DB_OPTIONS_DRIVER", default="ODBC Driver 17 for SQL Server"),
                "extra_params": env("DB_OPTIONS_EXTRA_PARAMS", default=""),
            },
        }
    )

# Base de datos externa KACTUS para integracion de empleados
DATABASES["kactus"] = {
    "ENGINE": "mssql",
    "NAME": "KACTUS",
    "USER": "seven",
    "PASSWORD": "SevenIps1a*",
    "HOST": "172.27.198.73",
    "PORT": "",
    "OPTIONS": {
        "driver": "ODBC Driver 18 for SQL Server",
        "extra_params": "Encrypt=no;TrustServerCertificate=yes;",
    },
}

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.CedulaExpedicionBackend",
]

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SESSION_COOKIE_AGE = 28800
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
CSRF_USE_SESSIONS = True
CSRF_FAILURE_VIEW = "config.views.csrf_failure"

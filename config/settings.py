from pathlib import Path
import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-rhzytm^%11%-^noecnpzmruy7_s_6*z&#hzyh+q0@nwb7j6(-v')
SHOW_SWAGGER = int(os.getenv('DJANGO_SHOW_SWAGGER', 1))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = int(os.getenv('DEBUG', 1))

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '127.0.0.1').split(",")
# CSRF_TRUSTED_ORIGINS = os.getenv("CSRF_TRUSTED_ORIGINS").split(",")

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # apps
    "authorization",
    "service",
    "base",

    # packages
    "rest_framework",
    "drf_yasg",
    "corsheaders",
    "tinymce",
    "rest_framework_simplejwt",
    "modeltranslation",
    'ckeditor',
    'ckeditor_uploader',  # For image/file upload suppert
    'payment'

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'x-api-key',
    'content-type',
    'Authorization'
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'default'),
        'USER': os.getenv('DB_USER', 'default'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'default'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', 5432),
    }
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'authorization.custom_jwt.CustomJwtAuthentication',
    ),

}

JWT_USE = True
ACCESS_TOKEN_LIFETIME = timedelta(days=int(os.getenv('ACCESS_TOKEN_LIFETIME_DAYS', 1)))
REFRESH_TOKEN_LIFETIME = timedelta(days=int(os.getenv('REFRESH_TOKEN_LIFETIME_DAYS', 2)))

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': ACCESS_TOKEN_LIFETIME,
    'REFRESH_TOKEN_LIFETIME': REFRESH_TOKEN_LIFETIME,
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'ru-ru'

get_text = lambda x: x
LANGUAGES = {
    'uz': get_text('Uzbek'),
    'ru': get_text('Russian'),
    'en': get_text('English')
}

MODELTRANSLATION_DEFAULT_LANGUAGE = 'ru'
MODELTRANSLATION_LANGUAGES = ('uz', 'ru', 'en')

TIME_ZONE = 'Asia/Tashkent'

USE_I18N = True

USE_TZ = False

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# CKEditor upload path
CKEDITOR_UPLOAD_PATH = "uploads/"
# CKEDITOR_IMAGE_BACKEND = "pillow"
# CKEDITOR_ALLOW_NONIMAGE_FILES = True

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

TELEGRAM_BOT_TOKEN = "6380957235:AAHOgqvvnffZL4deU_pY79mieYdBJYr0J-w"
TELEGRAM_CHANNEL_ID = "-1002522360493"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage?chat_id={TELEGRAM_CHANNEL_ID}&text="

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'jwt': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    },
    'SWAGGER_UI_REQUEST_HEADERS': [
        {
            'name': 'Authorization',
            'description': 'JWT Token',
            'value': 'Bearer <your_jwt_token_here>'
        },
    ],
    'LOGIN_URL': 'api/v1/auth/login',
    "DEFAULT_MODEL_RENDERING": "example"
}

CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'Full',
        'height': 400,
        'width': '100%',
        'tabSpaces': 4,

        # Enable content embedding (YouTube, Vimeo, etc.)
        'extraPlugins': ','.join([
            'uploadimage',  # allow image uploads
            # 'uploadfile',       # allow file uploads
            'embed',  # for oEmbed videos
            'autoembed',  # automatically embed URLs
            'image2',  # enhanced image plugin
            'codesnippet',  # code blocks with syntax highlighting
            'autogrow',  # auto-resize editor
            'clipboard',  # copy/paste features
            'justify',  # text alignment
            'colorbutton',  # text color
            'font',  # font options
            # 'video',            # optional video plugin
        ]),

        'toolbar_Full': [
            {'name': 'document', 'items': ['Source', '-', 'Preview', 'Print']},
            {'name': 'clipboard', 'items': ['Cut', 'Copy', 'Paste', 'PasteText', 'PasteFromWord', '-', 'Undo', 'Redo']},
            {'name': 'editing', 'items': ['Find', 'Replace', '-', 'SelectAll']},
            {'name': 'styles', 'items': ['Format', 'Font', 'FontSize']},
            {'name': 'basicstyles', 'items': ['Bold', 'Italic', 'Underline', 'Strike', '-', 'RemoveFormat']},
            {'name': 'colors', 'items': ['TextColor', 'BGColor']},
            {'name': 'paragraph',
             'items': ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', '-', 'Blockquote', '-', 'JustifyLeft',
                       'JustifyCenter', 'JustifyRight', 'JustifyBlock']},
            {'name': 'links', 'items': ['Link', 'Unlink', 'Anchor']},
            {'name': 'insert',
             'items': ['Image', 'UploadImage', 'Table', 'HorizontalRule', 'Smiley', 'SpecialChar', 'Embed',
                       'CodeSnippet']},
            {'name': 'tools', 'items': ['Maximize', 'ShowBlocks']},
        ],

        'codeSnippet_theme': 'monokai_sublime',
        'autoGrow_minHeight': 200,
        'autoGrow_maxHeight': 800,
        'autoGrow_bottomSpace': 50,

        # Optional: limit allowed content to avoid security issues
        'allowedContent': True,
        'removePlugins': 'stylesheetparser',
        'forcePasteAsPlainText': False,
        'embed_provider': '//ckeditor.iframe.ly/api/oembed?url={url}&callback={callback}',
    }
}

# click_settings
CLICK_SERVICE_ID = int(os.getenv('CLICK_SERVICE_ID', 1))
CLICK_MERCHANT_ID = int(os.getenv('CLICK_MERCHANT_ID', 1))
CLICK_SECRET_KEY = os.getenv('CLICK_SECRET_KEY', "")
CLICK_ACCOUNT_MODEL = os.getenv('CLICK_ACCOUNT_MODEL', "")
CLICK_AMOUNT_FIELD = os.getenv('CLICK_AMOUNT_FIELD', "")

# payme_settings
PAYME_ID = int(os.getenv('PAYME_ID', 1))
PAYME_KEY = os.getenv('PAYME_KEY', "")

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

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '127.0.0.1').split(',')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    #apps
    "authorization",
    "service",

    #packages
    "rest_framework",
    "drf_yasg",
    "corsheaders",
    "tinymce",
    "rest_framework_simplejwt",
    "modeltranslation"

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
        'authorization.custom_jwt.CustomJWTAuthentication',
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

LANGUAGE_CODE = 'en-us'

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

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

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

TINYMCE_DEFAULT_CONFIG = {
    'height': 500,
    'width': '100%',
    'plugins': 'advlist autolink lists link image charmap preview anchor '
               'searchreplace visualblocks code fullscreen insertdatetime media table paste help',
    'toolbar': 'undo redo | styleselect | bold italic | link image media | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | removeformat | help',
    'image_advtab': True,  # Enables advanced image options
    'file_picker_callback': 'function(callback, value, meta) { \
        if (meta.filetype === "image") { \
            var input = document.createElement("input"); \
            input.setAttribute("type", "file"); \
            input.setAttribute("accept", "image/*"); \
            input.onchange = function() { \
                var file = this.files[0]; \
                var reader = new FileReader(); \
                reader.onload = function() { \
                    callback(reader.result, { alt: file.name }); \
                }; \
                reader.readAsDataURL(file); \
            }; \
            input.click(); \
        } \
    }',
}
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880

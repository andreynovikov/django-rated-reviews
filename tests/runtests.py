#!/usr/bin/env python

"""
Adapted from django-contrib-comments, wich itself was adapted from django-constance,
which itself was adapted from django-adminfiles. :)
"""

import os
import sys
from importlib.util import find_spec

import django

from django.test.runner import DiscoverRunner
from django.conf import settings


here = os.path.dirname(os.path.abspath(__file__))
parent = os.path.dirname(here)
sys.path[0:0] = [here, parent]

# REST API is optional, it is tested only if Django REST framework is installed
HAS_DRF = find_spec('rest_framework') is not None

settings.configure(
    DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3'}},
    INSTALLED_APPS=[
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.messages",
        "django.contrib.sessions",
        "django.contrib.sites",
        "django.contrib.admin",
        "reviews",
        "testapp",
        "custom_reviews",
        "api_reviews",
    ] + (["rest_framework"] if HAS_DRF else []),
    MIDDLEWARE=(
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
    ),
    ROOT_URLCONF='testapp.urls',
    TEMPLATES=[
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'APP_DIRS': True,
            'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.request',
                    'django.contrib.auth.context_processors.auth',
                    'django.contrib.messages.context_processors.messages',
                ]
            },
        },
    ],
    SECRET_KEY="it's a secret to everyone",
    SITE_ID=1,
    # Intentionally differs from reviews app default_auto_field to ensure
    # that reviews migrations do not depend on project settings
    DEFAULT_AUTO_FIELD='django.db.models.AutoField'
)


def main(test_labels=None):
    django.setup()
    runner = DiscoverRunner(failfast=True, verbosity=1)
    failures = runner.run_tests(test_labels or ['testapp'], interactive=True)
    sys.exit(failures)


if __name__ == '__main__':
    test_labels = None
    if len(sys.argv) > 1:
        test_labels = sys.argv[1:]
    main(test_labels)

import os

import django
import pytest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')


def pytest_configure(config):
    django.setup()


@pytest.fixture(scope='session')
def live_server():
    return 'http://localhost:9000'

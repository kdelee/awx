import pytest
import logging
import importlib

from django.db.models.signals import post_migrate

from awx.main.utils import is_testing

from unittest.mock import PropertyMock

from awx.api.urls import urlpatterns as api_patterns
from awx.main.models import ExecutionEnvironment

# Django
from django.urls import URLResolver, URLPattern


# Keep direct unit-test runs aligned with the functional test setup. DAB's
# resource-registry signal requires ServiceID during post-migrate, but unit
# pytest collection does not load tests/functional/conftest.py. Revert this
# local hook if the shared test bootstrap starts loading that fixture instead.
def _create_service_id(app_config, apps=None, **kwargs):
    if apps is None:
        return
    try:
        apps.get_model('dab_resource_registry', 'ServiceID')
    except LookupError:
        return
    importlib.import_module('ansible_base.resource_registry.migrations.0001_initial').create_service_id(apps, None)


if is_testing():
    post_migrate.connect(_create_service_id)


@pytest.fixture()
def execution_environment():
    return ExecutionEnvironment(name="test-ee", description="test-ee", managed=True)


@pytest.fixture(autouse=True)
def _disable_database_settings(mocker):
    m = mocker.patch('awx.conf.settings.SettingsWrapper.all_supported_settings', new_callable=PropertyMock)
    m.return_value = []


@pytest.fixture()
def all_views():
    """
    returns a set of all views in the app
    """
    patterns = set()
    url_views = set()
    # Add recursive URL patterns
    unprocessed = set(api_patterns)
    while unprocessed:
        to_process = unprocessed.copy()
        unprocessed = set()
        for pattern in to_process:
            if hasattr(pattern, 'lookup_str') and not pattern.lookup_str.startswith('awx.api'):
                continue
            patterns.add(pattern)
            if isinstance(pattern, URLResolver):
                for sub_pattern in pattern.url_patterns:
                    if sub_pattern not in patterns:
                        unprocessed.add(sub_pattern)
    # Get view classes
    for pattern in patterns:
        if isinstance(pattern, URLPattern) and hasattr(pattern.callback, 'view_class'):
            url_views.add(pattern.callback.view_class)
    return url_views


@pytest.fixture()
def dummy_log_record():
    return logging.LogRecord(
        'awx',  # logger name
        20,  # loglevel INFO
        './awx/some/module.py',  # pathname
        100,  # lineno
        'User joe logged in',  # msg
        tuple(),  # args,
        None,  # exc_info
    )

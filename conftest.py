import os

SHOW_BROWSER = False


def pytest_addoption(parser):
    parser.addoption("--show-browser", action="store_true", default=False)


def pytest_configure(config):
    os.environ['TESTS_SHOW_BROWSER'] = 'TRUE'

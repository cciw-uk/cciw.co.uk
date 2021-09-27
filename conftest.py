import os

SHOW_BROWSER = False


def pytest_addoption(parser):
    parser.addoption("--show-browser", action="store_true", default=False, help="Show web browser window")


def pytest_configure(config):
    if config.option.show_browser:
        os.environ["TESTS_SHOW_BROWSER"] = "TRUE"
